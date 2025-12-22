"""
NTIC2 Memory System - Adapted for SmartPresence
EXACT NTIC2 SIGNATURES, using SmartPresence database internally
"""
import logging
from typing import List, Dict
from app.db.session import SessionLocal
from app.models.chatbot import ChatbotConversation, ChatbotMessage

logger = logging.getLogger(__name__)

MAX_CONTEXT_MESSAGES = 10


def save_turn(user_id, user_message, assistant_message):
    """
    Save conversation turn (EXACT NTIC2 signature)
    Gets its own DB connection like NTIC2
    """
    if not user_id or not user_message or not assistant_message:
        logger.warning(f"Invalid data: user_id={user_id}")
        return False
    
    db = SessionLocal()
    try:
        # Get or create conversation
        conversation = db.query(ChatbotConversation).filter_by(
            user_id=int(user_id),
            is_active=True
        ).first()
        
        if not conversation:
            conversation = ChatbotConversation(
                user_id=int(user_id),
                is_active=True
            )
            db.add(conversation)
            db.flush()
        
        # Save user message
        user_msg = ChatbotMessage(
            conversation_id=conversation.id,
            role="user",
            content=user_message[:10000]
        )
        db.add(user_msg)
        
        # Save assistant message
        assistant_msg = ChatbotMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_message[:10000]
        )
        db.add(assistant_msg)
        
        db.commit()
        logger.info(f"Turn saved for user_id: {user_id} (user: {len(user_message)} chars, assistant: {len(assistant_message)} chars)")
        return True
    except Exception as e:
        logger.error(f"Error saving turn: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def load_context(user_id, limit=MAX_CONTEXT_MESSAGES, max_tokens=None):
    """
    Load conversation context (EXACT NTIC2 signature)
    Gets its own DB connection like NTIC2
    Returns: List[Dict] with {"role": "user/assistant", "content": "..."}
    """
    db = SessionLocal()
    try:
        # Get active conversation
        conversation = db.query(ChatbotConversation).filter_by(
            user_id=int(user_id),
            is_active=True
        ).first()
        
        if not conversation:
            return []
        
        # Get messages (limit * 2 for user+assistant pairs)
        messages = db.query(ChatbotMessage).filter_by(
            conversation_id=conversation.id
        ).order_by(ChatbotMessage.created_at.desc()).limit(limit * 2).all()
        
        # Reverse to chronological order
        messages = list(reversed(messages))
        
        # Format as NTIC2 expects
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        logger.info(f"Loaded {len(formatted_messages)} messages for user_id: {user_id}")
        return formatted_messages
    except Exception as e:
        logger.error(f"Error loading context: {e}")
        return []
    finally:
        db.close()


def clear_conversation(user_id):
    """
    Clear conversation history (EXACT NTIC2 signature)
    Gets its own DB connection like NTIC2
    """
    db = SessionLocal()
    try:
        conversation = db.query(ChatbotConversation).filter_by(
            user_id=int(user_id),
            is_active=True
        ).first()
        
        if conversation:
            conversation.is_active = False
            db.commit()
            logger.info(f"Cleared conversation for user_id: {user_id}")
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        db.rollback()
    finally:
        db.close()
