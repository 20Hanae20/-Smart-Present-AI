"""
Conversation memory module for chat history
Simple in-memory cache (can be extended to Redis/DB)
"""
import json
from collections import defaultdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Simple in-memory conversation history
_conversations = defaultdict(list)
_max_history = 10  # Keep last 10 turns per user

def save_turn(user_id: str, message: str, response: str):
    """Save a conversation turn"""
    try:
        turn = {
            "timestamp": datetime.now().isoformat(),
            "user": message,
            "assistant": response
        }
        _conversations[user_id].append(turn)
        # Keep only last N turns
        if len(_conversations[user_id]) > _max_history:
            _conversations[user_id] = _conversations[user_id][-_max_history:]
    except Exception as e:
        logger.warning(f"Error saving conversation turn: {e}")

def load_context(user_id: str, limit: int = 2):
    """Load recent conversation history"""
    try:
        if user_id not in _conversations:
            return []
        
        history = _conversations[user_id][-limit:] if limit else _conversations[user_id]
        
        # Convert to chat format for LLM
        messages = []
        for turn in history:
            messages.append({"role": "user", "content": turn["user"]})
            messages.append({"role": "assistant", "content": turn["assistant"]})
        
        return messages
    except Exception as e:
        logger.warning(f"Error loading conversation context: {e}")
        return []

def clear_conversation(user_id: str):
    """Clear conversation history for a user"""
    try:
        if user_id in _conversations:
            del _conversations[user_id]
    except Exception as e:
        logger.warning(f"Error clearing conversation: {e}")
