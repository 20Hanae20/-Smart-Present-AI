from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.student import Student
from app.models.user import User
from app.schemas.auth import (
    EnrollFacialRequest,
    FacialLoginRequest,
    LoginRequest,
    MeResponse,
    Token,
)
from app.services import auth as auth_service
from app.services.facial import enroll_user_faces, verify_user_face_by_image
from app.services.face_engine import warm_up_face_engine
from app.utils.deps import get_db
from app.utils.rate_limit import hit

router = APIRouter()
settings = get_settings()

# Backward-compatible re-export used by many route modules.
get_current_user = auth_service.get_current_user


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Verify password
    if not auth_service.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = auth_service.create_access_token(subject=str(user.id))
    user.last_login = datetime.now()
    db.add(user)
    db.commit()
    return token


@router.post("/login/facial", response_model=Token)
def login_facial(payload: FacialLoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    allowed, count, reset_at = hit(
        f"rate:facial_login:{payload.email}:{ip}",
        limit=10,
        window_seconds=300,
    )
    if not allowed:
        db.execute(
            text(
                "INSERT INTO facial_verification_logs (attempted_email, success, failure_reason, ip_address, user_agent) "
                "VALUES (:email, false, :reason, :ip, :ua)"
            ),
            {
                "email": payload.email,
                "reason": f"rate_limited:{count}",
                "ip": ip,
                "ua": request.headers.get("user-agent"),
            },
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many attempts. Try again after {datetime.fromtimestamp(reset_at).isoformat()}",
        )

    if not payload.image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Face image is required"
        )
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        # Log attempt (unknown email)
        db.execute(
            text(
                "INSERT INTO facial_verification_logs (attempted_email, success, failure_reason, ip_address, user_agent) "
                "VALUES (:email, false, :reason, :ip, :ua)"
            ),
            {
                "email": payload.email,
                "reason": "user_not_found",
                "ip": ip,
                "ua": request.headers.get("user-agent"),
            },
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    student = db.query(Student).filter(Student.user_id == user.id).first()
    student_id = student.id if student else None
    has_embeddings = db.execute(
        text(
            "SELECT 1 FROM facial_embeddings "
            "WHERE (user_id = :uid OR student_id = (:sid)::int) "
            "LIMIT 1"
        ),
        {"uid": user.id, "sid": student_id},
    ).fetchone()
    if not has_embeddings:
        # If face images exist on disk (from prior enrollment) but embeddings are missing
        # (e.g., after DB reset/migration), rebuild embeddings automatically.
        try:
            import os
            from pathlib import Path

            faces_dir = Path(os.getenv("FACE_STORAGE_DIR", "/app/storage/faces")) / str(user.id)
            if faces_dir.exists():
                image_paths_and_bytes = []
                for p in sorted(faces_dir.glob("*.jpg")):
                    with open(p, "rb") as f:
                        # Store a stable web path (matches admin_users.list_user_faces)
                        image_paths_and_bytes.append((f"/storage/faces/{user.id}/{p.name}", f.read()))

                if len(image_paths_and_bytes) >= 3:
                    enroll_user_faces(db, user.id, image_paths_and_bytes)

                    # Re-check now that we attempted to rebuild.
                    has_embeddings = db.execute(
                        text(
                            "SELECT 1 FROM facial_embeddings "
                            "WHERE (user_id = :uid OR student_id = (:sid)::int) "
                            "LIMIT 1"
                        ),
                        {"uid": user.id, "sid": student_id},
                    ).fetchone()
        except Exception:
            # If rebuild fails, fall back to the normal error path below.
            has_embeddings = has_embeddings

    if not has_embeddings:
        db.execute(
            text(
                "INSERT INTO facial_verification_logs (user_id, attempted_email, success, failure_reason, ip_address, user_agent) "
                "VALUES (:uid, :email, false, :reason, :ip, :ua)"
            ),
            {
                "uid": user.id,
                "email": payload.email,
                "reason": "no_enrolled_embeddings",
                "ip": request.client.host if request.client else None,
                "ua": request.headers.get("user-agent"),
            },
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No enrolled facial data for user"
        )
    import base64

    b64 = (
        payload.image_base64.split(",", 1)[1]
        if "," in payload.image_base64
        else payload.image_base64
    )
    try:
        img_bytes = base64.b64decode(b64)
    except Exception:
        db.execute(
            text(
                "INSERT INTO facial_verification_logs (user_id, attempted_email, success, failure_reason, ip_address, user_agent) "
                "VALUES (:uid, :email, false, :reason, :ip, :ua)"
            ),
            {
                "uid": user.id,
                "email": payload.email,
                "reason": "invalid_base64",
                "ip": request.client.host if request.client else None,
                "ua": request.headers.get("user-agent"),
            },
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid base64 face image"
        )
    threshold = payload.confidence_threshold or settings.facial_confidence_threshold

    matched_user_id, similarity, failure_reason, metrics = verify_user_face_by_image(
        db,
        email=payload.email,
        image_bytes=img_bytes,
        threshold=threshold,
    )

    db.execute(
        text(
            "INSERT INTO facial_verification_logs "
            "(user_id, attempted_email, success, similarity, threshold, failure_reason, num_faces, blur_score, brightness, ip_address, user_agent) "
            "VALUES (:uid, :email, :success, :sim, :thr, :reason, :faces, :blur, :bright, :ip, :ua)"
        ),
        {
            "uid": user.id,
            "email": payload.email,
            "success": bool(matched_user_id),
            "sim": float(similarity) if similarity is not None else None,
            "thr": float(threshold),
            "reason": failure_reason,
            "faces": int(metrics.num_faces) if metrics else None,
            "blur": float(metrics.blur_score) if metrics else None,
            "bright": float(metrics.brightness) if metrics else None,
            "ip": request.client.host if request.client else None,
            "ua": request.headers.get("user-agent"),
        },
    )
    db.commit()

    if not matched_user_id:
        if failure_reason in {"expected_single_face", "image_too_blurry", "image_too_dark", "image_too_bright", "face_too_small", "invalid_image"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Face image quality issue: {failure_reason}",
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Face not recognized")

    token = auth_service.create_access_token(subject=str(matched_user_id))
    return token


@router.get("/login/facial/prewarm", response_model=dict)
def login_facial_prewarm():
    """Preload the face engine to reduce first-request latency."""
    ready = warm_up_face_engine()
    if not ready:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to prewarm face engine")
    return {"status": "ready"}


@router.post("/enroll", response_model=dict)
def enroll_face(
    payload: EnrollFacialRequest,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin" and current_user.id != payload.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to enroll facial data for another user",
        )
    if not payload.requires_three_images():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Provide at least 3 images"
        )
    import base64

    image_bytes_list = []
    for idx, img in enumerate(payload.images_base64):
        b64 = img.split(",", 1)[1] if "," in img else img
        try:
            decoded = base64.b64decode(b64)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid base64 image at index {idx}",
            )
        image_bytes_list.append((f"uploaded_{idx}.jpg", decoded))
    try:
        inserted = enroll_user_faces(db, payload.user_id, image_bytes_list)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    student = db.query(Student).filter(Student.user_id == payload.user_id).first()
    if student:
        student.facial_data_encoded = True
        db.add(student)
        db.commit()
    return {"status": "enrolled", "user_id": payload.user_id, "images_processed": inserted}


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(auth_service.get_current_user)):
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        last_login=current_user.last_login,
    )
