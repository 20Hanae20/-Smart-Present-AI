"""
Smart Presence AI Agent - EXACT NTIC2 Integration
Intelligent chatbot with RAG, multi-provider LLM, and streaming capabilities
"""

from .core import agent_run_streaming, call_llm
from .rag_pipeline import rag_answer, get_embedding_function, init_collection
from .memory import save_turn, load_context, clear_conversation

__all__ = [
    # Core functions (EXACT NTIC2)
    "agent_run_streaming",
    "call_llm",
    
    # RAG pipeline
    "rag_answer", 
    "get_embedding_function",
    "init_collection",
    
    # Memory management
    "save_turn",
    "load_context", 
    "clear_conversation",
]
