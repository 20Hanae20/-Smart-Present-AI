from __future__ import annotations

import os
import threading
from dataclasses import dataclass

import cv2
import numpy as np
from insightface.app import FaceAnalysis


@dataclass(frozen=True)
class FaceQualityMetrics:
    num_faces: int
    blur_score: float
    brightness: float
    face_width: int
    face_height: int


class FaceQualityError(ValueError):
    def __init__(self, reason: str, metrics: FaceQualityMetrics | None = None):
        super().__init__(reason)
        self.reason = reason
        self.metrics = metrics


_face_app: FaceAnalysis | None = None
_face_app_lock = threading.Lock()


def _get_face_app() -> FaceAnalysis:
    global _face_app
    if _face_app is not None:
        return _face_app

    with _face_app_lock:
        if _face_app is not None:
            return _face_app

        os.environ.setdefault("INSIGHTFACE_HOME", os.getenv("INSIGHTFACE_HOME", "/app/storage/insightface"))
        model_name = os.getenv("INSIGHTFACE_MODEL", "buffalo_l")

        app = FaceAnalysis(name=model_name, providers=["CPUExecutionProvider"])
        # det_size is a practical default for selfie-sized images.
        # ctx_id=-1 forces CPU context.
        app.prepare(ctx_id=-1, det_size=(640, 640))
        _face_app = app
        return _face_app


def _decode_image_bytes_to_bgr(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image bytes")
    return img


def _compute_blur_and_brightness(img_bgr: np.ndarray) -> tuple[float, float]:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    return blur_score, brightness


def warm_up_face_engine() -> bool:
    """Ensure the InsightFace engine is loaded and ready.

    This preloads the model and runs a tiny no-op inference on a blank image
    to allocate internal buffers. Subsequent requests are faster.
    Returns True if the engine is ready.
    """
    try:
        app = _get_face_app()
        # Run a minimal forward pass to warm caches/graphs
        dummy = np.zeros((320, 320, 3), dtype=np.uint8)
        _ = app.get(dummy)
        return True
    except Exception:
        return False


def extract_embedding_with_quality(
    image_bytes: bytes,
    *,
    min_blur_score: float = 8.0,  # Lowered from 15.0 for webcam compatibility
    min_brightness: float = 40.0,
    max_brightness: float = 220.0,
    min_face_size: int = 80,
) -> tuple[np.ndarray, FaceQualityMetrics]:
    """Extract a 512D InsightFace embedding with basic quality gates.

    Raises `FaceQualityError` if the image is not suitable.
    """

    img_bgr = _decode_image_bytes_to_bgr(image_bytes)
    blur_score, brightness = _compute_blur_and_brightness(img_bgr)

    app = _get_face_app()
    faces = app.get(img_bgr)
    num_faces = len(faces)

    # Metrics defaults (for logging/diagnostics)
    face_w = 0
    face_h = 0
    if num_faces == 1:
        x1, y1, x2, y2 = faces[0].bbox.astype(int).tolist()
        face_w = max(0, x2 - x1)
        face_h = max(0, y2 - y1)

    metrics = FaceQualityMetrics(
        num_faces=num_faces,
        blur_score=blur_score,
        brightness=brightness,
        face_width=face_w,
        face_height=face_h,
    )

    if num_faces != 1:
        raise FaceQualityError("expected_single_face", metrics)

    if blur_score < min_blur_score:
        raise FaceQualityError("image_too_blurry", metrics)

    if brightness < min_brightness:
        raise FaceQualityError("image_too_dark", metrics)

    if brightness > max_brightness:
        raise FaceQualityError("image_too_bright", metrics)

    if face_w < min_face_size or face_h < min_face_size:
        raise FaceQualityError("face_too_small", metrics)

    emb = faces[0].embedding
    if emb is None:
        raise FaceQualityError("embedding_unavailable", metrics)

    emb = np.asarray(emb, dtype=np.float32)
    # Ensure unit norm (cosine similarity matches pgvector <=> expectations)
    norm = float(np.linalg.norm(emb) + 1e-8)
    emb = emb / norm

    if emb.shape[0] != 512:
        raise FaceQualityError("unexpected_embedding_size", metrics)

    return emb, metrics
