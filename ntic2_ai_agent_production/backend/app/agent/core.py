import os
import requests
import json
import time
import hashlib
import logging
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv # pyright: ignore[reportMissingImports]

from app.rag.pipeline import rag_answer
from app.memory import save_turn, load_context
from app.db.database import query_db

# Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(dotenv_path=project_root / '.env')

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama").lower()

# Cache simple pour performance
_question_cache = {}

def _get_cached_response(message):
    key = hashlib.md5(message.lower().strip().encode()).hexdigest()
    return _question_cache.get(key)

def _set_cached_response(message, response):
    if len(_question_cache) > 100: _question_cache.clear()
    key = hashlib.md5(message.lower().strip().encode()).hexdigest()
    _question_cache[key] = response

# Wrappers LLM
def call_llm(messages, stream=False):
    """Appelle le provider LLM configuré (priorité Groq pour la vitesse)"""
    if GROQ_API_KEY:
        try:
            return _call_groq(messages, stream=stream)
        except Exception as e:
            logger.warning(f"Groq a échoué, fallback sur Ollama: {e}")
    
    return _call_ollama(messages, stream=stream)

def _call_groq(messages, stream=False):
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.3,
        "stream": stream
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, stream=stream, timeout=30)
    response.raise_for_status()
    
    if stream:
        def generate():
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith("data: ") and "[DONE]" not in line_str:
                        try:
                            chunk = json.loads(line_str[6:])
                            content = chunk["choices"][0]["delta"].get("content")
                            if content: yield content
                        except: continue
        return generate()
    
    return response.json()["choices"][0]["message"]["content"]

def _call_ollama(messages, stream=False):
    prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    payload = {"model": "llama3.2:1b", "prompt": prompt, "stream": stream}
    response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, stream=stream, timeout=30)
    
    if stream:
        def generate():
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    if "response" in chunk: yield chunk["response"]
        return generate()
    
    return response.json().get("response", "")

# Logique principale
SYSTEM_PROMPT = """Tu es l'Assistant ISTA NTIC Sidi Maarouf.

Consignes:
- Réponds uniquement avec les informations présentes dans le contexte RAG fourni.
- Donne des réponses concrètes (listes, éléments, consignes) et évite les généralités.
- Quand c'est utile, cite les sources (titre + URL) à la fin sous la forme "Sources:".
- N'invente jamais de contenu. Si une information est absente, réponds: "Je n'ai pas cette information.".

Format:
- Utilise des listes à puces claires.
- Mets en évidence les éléments importants en gras.
"""

def agent_run_streaming(message, user_id):
    """Point d'entrée unique pour le chat, optimisé streaming"""
    # 1. Cache
    cached = _get_cached_response(message)
    if cached:
        yield json.dumps({"type": "start"}) + "\n"
        yield json.dumps({"type": "content", "content": cached["reply"]}) + "\n"
        yield json.dumps({"type": "end", "data": cached}) + "\n"
        return

    # 2. Contexte (RAG)
    detected_lang = 'ar' if re.search(r'[\u0600-\u06FF]', message) else 'fr'
    rag_context, sources = "", []
    try:
        section = "emplois du temps" if any(w in message.lower() for w in ['emploi', 'horaire', 'planning']) else None
        rag_context, sources = rag_answer(message, n_results=3, filter_section=section)
    except Exception as e:
        logger.error(f"RAG Error: {e}")

    # Enrichir le contexte avec l'emploi du temps depuis la base si demandé
    try:
        if any(w in message.lower() for w in ['emploi', 'horaire', 'planning']):
            group_codes = re.findall(r'\b[A-Za-z]{2,}\d{1,3}\b', message)
            if group_codes:
                from app.db.schedule_queries import get_schedule_by_groupe, format_schedule_response
                schedules = get_schedule_by_groupe(group_codes[0])
                if schedules:
                    schedule_text = format_schedule_response(schedules)
                    rag_context = f"{rag_context}\n\n===\nEMPLOI DU TEMPS:\n{schedule_text}" if rag_context else f"EMPLOI DU TEMPS:\n{schedule_text}"
    except Exception as e:
        logger.warning(f"DB schedule lookup error: {e}")

    # 3. Messages
    history = load_context(user_id, limit=2)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history: messages.extend(history)
    
    prompt = f"CONTEXTE:\n{rag_context}\n\nQUESTION: {message}" if rag_context else message
    messages.append({"role": "user", "content": prompt})

    # 4. Stream
    yield json.dumps({"type": "start"}) + "\n"
    full_answer = ""
    try:
        stream_gen = call_llm(messages, stream=True)
        for token in stream_gen:
            full_answer += token
            yield json.dumps({"type": "content", "content": token}) + "\n"
            
        final_data = {
            "reply": full_answer,
            "sources": [{"title": s.get("title", "Source"), "url": s.get("url", "")} for s in sources if isinstance(s, dict)],
            "rag_used": len(sources) > 0,
            "language": detected_lang
        }
        
        try: save_turn(user_id, message, full_answer)
        except: pass
        
        _set_cached_response(message, final_data)
        yield json.dumps({"type": "end", "data": final_data}) + "\n"
        
    except Exception as e:
        logger.error(f"Stream Error: {e}")
        yield json.dumps({"type": "error", "message": str(e)}) + "\n"
