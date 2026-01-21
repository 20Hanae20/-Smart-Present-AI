from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json
import logging

from app.db.session import get_db
from app.ai_agent.core import agent_run_streaming
from app.ai_agent.rag_pipeline import init_collection, rag_answer

router = APIRouter(tags=["chatbot"])
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"
    conversation_id: str = None

class ChatStatus(BaseModel):
    status: str
    rag_initialized: bool
    knowledge_documents: int
    streaming_available: bool
    providers_configured: list

@router.get("/status", response_model=ChatStatus)
async def status(db: Session = Depends(get_db)):
    """Get chatbot status and configuration"""
    try:
        # Check RAG initialization
        rag_initialized = False
        knowledge_documents = 0
        
        try:
            collection = init_collection()
            knowledge_documents = collection.count()
            rag_initialized = True
        except Exception as e:
            logger.warning(f"RAG not initialized: {e}")
        
        # Check available providers
        providers = []
        import os
        if os.getenv("GROQ_API_KEY"):
            providers.append("groq")
        if os.getenv("GOOGLE_API_KEY"):
            providers.append("gemini")
        if os.getenv("OPENAI_API_KEY"):
            providers.append("openai")
        
        return ChatStatus(
            status="ok" if providers else "no_providers",
            rag_initialized=rag_initialized,
            knowledge_documents=knowledge_documents,
            streaming_available=True,
            providers_configured=providers
        )
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return ChatStatus(
            status="error",
            rag_initialized=False,
            knowledge_documents=0,
            streaming_available=False,
            providers_configured=[]
        )

@router.post("/ask")
async def ask(request: ChatRequest, db: Session = Depends(get_db)):
    """Non-streaming chat endpoint"""
    try:
        # Collect full response from streaming
        full_response = ""
        sources = []
        
        for chunk_str in agent_run_streaming(request.message, request.user_id, db):
            try:
                chunk = json.loads(chunk_str) if isinstance(chunk_str, str) else chunk_str
                if chunk.get("type") == "content":
                    full_response += chunk.get("content", "")
                elif chunk.get("type") == "end":
                    sources = chunk.get("data", {}).get("sources", [])
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return {
            "reply": full_response,
            "sources": sources,
            "user_id": request.user_id,
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask/stream")
async def ask_stream(request: ChatRequest, db: Session = Depends(get_db)):
    """Streaming chat endpoint with Server-Sent Events"""
    try:
        async def generate():
            for chunk_str in agent_run_streaming(request.message, request.user_id, db):
                yield f"data: {chunk_str}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def stream(request: ChatRequest, db: Session = Depends(get_db)):
    """Alternative streaming endpoint (for frontend compatibility)"""
    return await ask_stream(request, db)

@router.post("/start")
async def start_conversation(request: ChatRequest, db: Session = Depends(get_db)):
    """Start a new conversation"""
    try:
        from app.ai_agent.memory import clear_conversation
        clear_conversation(request.user_id, db)
        
        return {
            "conversation_id": f"{request.user_id}_{__import__('time').time()}",
            "status": "started",
            "message": "Conversation started successfully"
        }
        
    except Exception as e:
        logger.error(f"Start conversation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{user_id}")
async def get_history(user_id: str, db: Session = Depends(get_db)):
    """Get conversation history for user"""
    try:
        from app.ai_agent.memory import load_context
        context = load_context(user_id, db)
        
        return {
            "user_id": user_id,
            "history": context,
            "total_messages": len(context)
        }
        
    except Exception as e:
        logger.error(f"History error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear/{user_id}")
async def clear_history(user_id: str, db: Session = Depends(get_db)):
    """Clear conversation history for user"""
    try:
        from app.ai_agent.memory import clear_conversation
        clear_conversation(user_id, db)
        
        return {
            "status": "cleared",
            "message": "Conversation history cleared"
        }
        
    except Exception as e:
        logger.error(f"Clear history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/{user_id}")
async def get_stats(user_id: str, db: Session = Depends(get_db)):
    """Get conversation statistics for user"""
    try:
        from app.ai_agent.memory import get_conversation_stats
        stats = get_conversation_stats(user_id, db)
        
        return stats
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/seed")
async def seed_knowledge(db: Session = Depends(get_db)):
    """Seed the knowledge base (admin only)"""
    try:
        from app.ai_agent.rag_pipeline import seed_smartpresence_knowledge
        seed_smartpresence_knowledge()
        
        return {
            "status": "seeded",
            "message": "Knowledge base seeded successfully"
        }
        
    except Exception as e:
        logger.error(f"Seed error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
