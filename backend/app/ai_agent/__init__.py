"""
AI Agent module for SmartPresence - EXACT NTIC2 integration
Provides RAG-powered chatbot with multi-provider LLM support.

EXACT NTIC2 APPROACH:
- Function-based, not class-based
- Direct calls to agent_run_streaming()
- ChromaDB for RAG with sentence-transformers
- Multi-provider fallback: Groq → Gemini → OpenAI
- Conversation memory in PostgreSQL
"""

# EXACT NTIC2: Export functions, not classes
from app.ai_agent.core import (
    agent_run_streaming,
    call_llm
)
from app.ai_agent.rag_pipeline import (
    rag_answer,
    get_chromadb_path,
    get_embedding_function
)
from app.ai_agent.memory import (
    save_turn,
    load_context,
    clear_conversation
)

__all__ = [
    # Core agent functions
    "agent_run_streaming",
    "call_llm",
    "_get_cached_response",
    "_set_cached_response",
    
    # RAG functions
    "rag_answer",
    "get_chromadb_path",
    "get_embedding_function",
    "init_collection",
    "seed_smartpresence_knowledge",
    
    # Memory functions
    "save_turn",
    "load_context",
    "clear_conversation",
]
