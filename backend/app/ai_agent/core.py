"""
Smart Presence AI Agent Core - EXACT NTIC2 Implementation
Multi-provider LLM with fallbacks, caching, and streaming support
"""

import json
import logging
import os
import hashlib
from typing import Dict, Any, Iterator, Optional

import redis
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Environment configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") 
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Redis cache (optional)
redis_client = None
try:
    if os.getenv("REDIS_CACHE_ENABLED", "false").lower() == "true":
        redis_client = redis.from_url(REDIS_URL)
        logger.info("Redis cache enabled")
except Exception as e:
    logger.warning(f"Redis cache disabled: {e}")

def _get_cache_key(message: str, user_id: str) -> str:
    """Generate cache key for message"""
    content = f"{message}:{user_id}"
    return hashlib.md5(content.encode()).hexdigest()

def _get_cached_response(message: str, user_id: str) -> Optional[str]:
    """Get cached response if available"""
    if not redis_client:
        return None
    
    try:
        key = _get_cache_key(message, user_id)
        cached = redis_client.get(key)
        return cached.decode() if cached else None
    except Exception as e:
        logger.warning(f"Cache get error: {e}")
        return None

def _set_cached_response(message: str, user_id: str, response: str, ttl: int = 3600):
    """Cache response for future use"""
    if not redis_client:
        return
    
    try:
        key = _get_cache_key(message, user_id)
        redis_client.setex(key, ttl, response)
    except Exception as e:
        logger.warning(f"Cache set error: {e}")

def _call_groq(messages: list, model: str = "llama3-70b-8192") -> str:
    """Call Groq API - Primary provider (fastest)"""
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
            stream=False
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        raise

def _call_gemini(messages: list, model: str = "gemini-1.5-flash") -> str:
    """Call Google Gemini API - Fallback 1"""
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=GOOGLE_API_KEY)
        model_instance = genai.GenerativeModel(model)
        
        # Convert messages to Gemini format
        prompt = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt += f"System: {content}\n\n"
            elif role == "user":
                prompt += f"User: {content}\n\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n\n"
        
        response = model_instance.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise

def _call_openai(messages: list, model: str = "gpt-3.5-turbo") -> str:
    """Call OpenAI API - Fallback 2 (last resort)"""
    try:
        import openai
        
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        raise

def call_llm(messages: list, user_id: str = "default") -> str:
    """
    Multi-provider LLM call with fallbacks
    Tries: Groq -> Gemini -> OpenAI
    """
    # Check cache first
    message_content = json.dumps(messages)
    cached = _get_cached_response(message_content, user_id)
    if cached:
        logger.info("Using cached response")
        return cached
    
    # Try providers in order
    providers = []
    
    if GROQ_API_KEY:
        providers.append(("Groq", _call_groq))
    
    if GOOGLE_API_KEY:
        providers.append(("Gemini", _call_gemini))
        
    if OPENAI_API_KEY:
        providers.append(("OpenAI", _call_openai))
    
    if not providers:
        raise ValueError("No LLM providers configured")
    
    last_error = None
    for provider_name, provider_func in providers:
        try:
            logger.info(f"Trying {provider_name}...")
            response = provider_func(messages)
            
            # Cache successful response
            _set_cached_response(message_content, user_id, response)
            
            logger.info(f"{provider_name} successful")
            return response
            
        except Exception as e:
            logger.warning(f"{provider_name} failed: {e}")
            last_error = e
            continue
    
    # All providers failed
    raise Exception(f"All LLM providers failed. Last error: {last_error}")

def agent_run_streaming(message: str, user_id: str = "default", db: Optional[Session] = None) -> Iterator[str]:
    """
    Main AI Agent entry point - EXACT NTIC2 implementation
    Handles RAG, conversation memory, LLM calls, and streaming
    """
    try:
        # Load conversation context
        context_messages = []
        if db:
            try:
                from .memory import load_context
                context_messages = load_context(user_id, db)
                logger.info(f"Loaded {len(context_messages)} context messages")
            except Exception as e:
                logger.warning(f"Failed to load context: {e}")
        
        # Check cache first
        cached_response = _get_cached_response(message, user_id)
        if cached_response:
            # Yield cached response as streaming
            for char in cached_response:
                yield json.dumps({
                    "type": "content",
                    "content": char
                })
            yield json.dumps({
                "type": "end",
                "data": {"reply": cached_response, "cached": True}
            })
            return
        
        # RAG retrieval
        rag_context = ""
        sources = []
        try:
            from .rag_pipeline import rag_answer
            rag_result = rag_answer(message)
            
            if rag_result and rag_result.get("answer"):
                rag_context = rag_result["answer"]
                sources = rag_result.get("sources", [])
                logger.info(f"RAG found {len(sources)} sources")
        except Exception as e:
            logger.warning(f"RAG failed: {e}")
        
        # Build messages for LLM
        system_prompt = """Tu es un assistant intelligent pour Smart Presence AI, un système de gestion des présences avec reconnaissance faciale.

Aide les utilisateurs avec:
- Les procédures de check-in/check-out
- La consultation des présences et absences  
- Les justifications d'absence
- Les informations sur les sessions et formateurs
- L'utilisation des fonctionnalités de reconnaissance faciale
- Les problèmes techniques courants

Sois utile, précis et professionnel. Si tu utilises des informations provenant de documents sources, mentionne-le."""
        
        if rag_context:
            system_prompt += f"\n\nContexte pertinent:\n{rag_context}"
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history (last 10 messages)
        for ctx_msg in context_messages[-10:]:
            if ctx_msg.get("role") == "user":
                messages.append({"role": "user", "content": ctx_msg.get("content", "")})
            elif ctx_msg.get("role") == "assistant":
                messages.append({"role": "assistant", "content": ctx_msg.get("content", "")})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Get LLM response
        response = call_llm(messages, user_id)
        
        # Stream response
        for char in response:
            yield json.dumps({
                "type": "content", 
                "content": char
            })
        
        # Save to memory
        if db:
            try:
                from .memory import save_turn
                save_turn(user_id, message, response, db)
                logger.info("Saved to memory")
            except Exception as e:
                logger.warning(f"Failed to save to memory: {e}")
        
        # Send final chunk with sources
        yield json.dumps({
            "type": "end",
            "data": {
                "reply": response,
                "sources": sources,
                "rag_used": len(sources) > 0
            }
        })
        
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        yield json.dumps({
            "type": "error",
            "message": f"Erreur: {str(e)}"
        })
