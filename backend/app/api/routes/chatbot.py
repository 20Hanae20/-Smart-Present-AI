from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["chatbot"])


def _gone():
  raise HTTPException(status_code=410, detail="Legacy chatbot removed. Use NTIC2 service at http://localhost:8080.")


@router.get("/status")
def status():
  _gone()


@router.post("/ask")
def ask():
  _gone()


@router.post("/ask/stream")
def ask_stream():
  _gone()


@router.post("/start")
def start():
  _gone()


@router.get("/history/{conversation_id}")
def history(conversation_id: int):
  _gone()


@router.post("/message/{conversation_id}")
def message(conversation_id: int, message: str):
  _gone()


@router.post("/close/{conversation_id}")
def close(conversation_id: int):
  _gone()


@router.post("/feedback/{conversation_id}")
def feedback(conversation_id: int, score: int, feedback: str | None = None):
  _gone()
