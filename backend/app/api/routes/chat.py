"""
RAG-powered chat endpoint for NTIC2 AI Assistant
Integrated into SmartPresence for unified chatbot experience
"""
import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

try:
    from app.rag.pipeline import rag_answer
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

class ChatMessage(BaseModel):
    message: str
    user_id: str = "student"

@router.post("/message")
async def chat_message(req: ChatMessage):
    """Non-streaming chat endpoint for quick responses"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG pipeline not available")
    
    try:
        # Get RAG context
        rag_context, sources = rag_answer(req.message, n_results=3)
        
        # If we have RAG context, return it directly (simple mode)
        if rag_context:
            return {
                "reply": rag_context,
                "sources": [{"title": s.get("title", "Source"), "url": s.get("url", "")} for s in sources if isinstance(s, dict)],
                "rag_used": True
            }
        else:
            return {
                "reply": "Je n'ai pas trouvé d'information pertinente. Veuillez reformuler votre question.",
                "sources": [],
                "rag_used": False
            }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def chat_stream(req: ChatMessage):
    """Streaming chat endpoint (SSE format for frontend)"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG pipeline not available")
    
    async def generate():
        try:
            # Get RAG context
            rag_context, sources = rag_answer(req.message, n_results=3)
            
            # Start response
            yield f"data: {json.dumps({'type': 'start'})}\n\n"
            
            # Stream context as chunks (simulating streaming)
            if rag_context:
                # Send the content in reasonable chunks
                chunk_size = 50
                for i in range(0, len(rag_context), chunk_size):
                    chunk = rag_context[i:i+chunk_size]
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
            
            # End with sources
            final_data = {
                "reply": rag_context,
                "sources": [{"title": s.get("title", "Source"), "url": s.get("url", "")} for s in sources if isinstance(s, dict)],
                "rag_used": len(sources) > 0
            }
            yield f"data: {json.dumps({'type': 'end', 'data': final_data})}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@router.get("/status")
async def chat_status():
    """Check RAG pipeline status and chunk count"""
    if not RAG_AVAILABLE:
        return {"status": "unavailable", "chunks": 0}
    
    try:
        import chromadb
        from app.rag.pipeline import get_chromadb_path
        
        client = chromadb.PersistentClient(path=get_chromadb_path())
        try:
            collection = client.get_collection(name="website_content")
            count = len(collection.get()["ids"])
            return {"status": "ok", "chunks": count, "connected": True}
        except:
            return {"status": "no_data", "chunks": 0, "connected": True}
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return {"status": "error", "chunks": 0, "connected": False}
