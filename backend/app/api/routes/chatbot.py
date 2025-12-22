from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.chatbot import (
    ChatbotAskIn,
    ChatbotConversationOut,
    ChatbotMessageOut,
)
from app.services.chatbot import ChatbotService
from app.ai_agent.core import agent_run_streaming  # EXACT NTIC2: direct function import
from app.utils.deps import get_current_user, get_db

router = APIRouter(tags=["chatbot"])


@router.post("/start", response_model=ChatbotConversationOut)
def start_conversation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a new chatbot conversation."""
    conversation = ChatbotService.start_conversation(db, current_user.id, current_user.role)
    return conversation


@router.post("/message/{conversation_id}", response_model=ChatbotMessageOut)
def send_message(
    conversation_id: int,
    message: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message to chatbot and get response."""
    response = ChatbotService.send_message(db, conversation_id, message)
    if not response:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return response


@router.get("/history/{conversation_id}")
def get_conversation_history(
    conversation_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get conversation history."""
    messages = ChatbotService.get_conversation_history(db, conversation_id, limit)
    return {"conversation_id": conversation_id, "messages": messages, "count": len(messages)}


@router.post("/close/{conversation_id}")
def close_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Close a conversation."""
    conversation = ChatbotService.close_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "closed", "conversation_id": conversation.id}


@router.post("/feedback/{conversation_id}")
def set_satisfaction(
    conversation_id: int,
    score: int,
    feedback: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set user satisfaction with chatbot."""
    if not 1 <= score <= 5:
        raise HTTPException(status_code=400, detail="Score must be between 1 and 5")

    conversation = ChatbotService.set_satisfaction_score(db, conversation_id, score, feedback)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "score": score}


@router.post("/ask")
def ask_quick(
    question: str | None = None,
    payload: ChatbotAskIn | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Quick ask endpoint (no conversation tracking).

    Supports both query param `question` and JSON body `{ "question": "..." }`.
    """
    q = question or (payload.question if payload else None)
    if not q:
        raise HTTPException(status_code=422, detail="Field 'question' is required")
    
    # Build user context
    user_context = {
        "role": current_user.role,
        "user_id": current_user.id,
    }
    
    # Generate response using new AI Agent
    response_data = ChatbotService.generate_response(q, user_context, db)
    intent = ChatbotService.detect_intent(q)
    
    # For frontend compatibility, return 'response' key
    return {
        "question": q,
        "response": response_data.get("reply", ""),
        "intent": intent,
        "sources": response_data.get("sources", []),
        "rag_used": response_data.get("rag_used", False),
    }


@router.post("/ask/stream")
def ask_streaming(
    payload: ChatbotAskIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Streaming ask endpoint for real-time responses (EXACT NTIC2 approach).
    Returns Server-Sent Events (SSE) stream.
    """
    if not payload or not payload.question:
        raise HTTPException(status_code=422, detail="Field 'question' is required")
    
    def generate():
        """SSE generator function - EXACT NTIC2 streaming pattern."""
        import json
        try:
            # EXACT NTIC2: Direct function call with streaming
            for chunk in agent_run_streaming(
                message=payload.question,
                user_id=current_user.id,
                db_session=db
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
)
@router.get("/status")
def get_chatbot_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get chatbot and RAG pipeline status (EXACT NTIC2 approach)."""
    import chromadb
    from app.ai_agent.rag_pipeline import get_chromadb_path
    
    try:
        # EXACT NTIC2: Direct ChromaDB check
        client = chromadb.PersistentClient(path=get_chromadb_path())
        
        try:
            collection = client.get_collection(name="smartpresence_knowledge")
            doc_count = collection.count()
            initialized = True
        except Exception:
            doc_count = 0
            initialized = False
        
        return {
            "status": "ok",
            "rag_initialized": initialized,
            "knowledge_documents": doc_count,
            "streaming_available": True,
            "chroma_path": get_chromadb_path()
        }
    except Exception as e:
        return {
            "status": "degraded",
            "rag_initialized": False,
            "knowledge_documents": 0,
            "streaming_available": True,
            "error": str(e)
        }
