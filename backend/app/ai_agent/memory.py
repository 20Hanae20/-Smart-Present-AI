"""
Smart Presence AI Memory - EXACT NTIC2 Implementation
Conversation history management using PostgreSQL
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def save_turn(user_id: str, user_message: str, assistant_response: str, db: Session, 
               conversation_id: Optional[str] = None):
    """
    Save a conversation turn to PostgreSQL database
    """
    try:
        from app.models.chatbot import ChatbotConversation, ChatbotMessage
        
        # Get or create conversation
        if conversation_id:
            conversation = db.query(ChatbotConversation).filter(
                ChatbotConversation.session_id == conversation_id
            ).first()
        else:
            # Find active conversation for user or create new
            conversation = db.query(ChatbotConversation).filter(
                ChatbotConversation.user_id == int(user_id) if user_id.isdigit() else 1,
                ChatbotConversation.is_active == True
            ).order_by(ChatbotConversation.last_activity.desc()).first()
        
        if not conversation:
            # Create new conversation
            conversation = ChatbotConversation(
                user_id=int(user_id) if user_id.isdigit() else 1,
                user_type="student",  # Default, could be detected
                session_id=f"{user_id}_{datetime.now().timestamp()}",
                context_data=json.dumps({}),
                conversation_history=json.dumps([]),
                is_active=True,
                message_count=0,
            )
            db.add(conversation)
            db.flush()  # Get the ID
        
        # Save user message
        user_msg = ChatbotMessage(
            conversation_id=conversation.id,
            message_type="user",
            content=user_message,
            created_at=datetime.utcnow()
        )
        db.add(user_msg)
        
        # Save assistant response
        assistant_msg = ChatbotMessage(
            conversation_id=conversation.id,
            message_type="assistant", 
            content=assistant_response,
            created_at=datetime.utcnow()
        )
        db.add(assistant_msg)
        
        # Update conversation
        conversation.message_count += 2
        conversation.last_activity = datetime.utcnow()
        
        # Update conversation history (JSON field)
        try:
            history = json.loads(conversation.conversation_history or "[]")
            history.append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.utcnow().isoformat()
            })
            history.append({
                "role": "assistant", 
                "content": assistant_response,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Keep only last 20 messages in JSON history
            if len(history) > 20:
                history = history[-20:]
            
            conversation.conversation_history = json.dumps(history)
        except Exception as e:
            logger.warning(f"Failed to update conversation history: {e}")
        
        db.commit()
        logger.debug(f"Saved conversation turn for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to save conversation turn: {e}")
        db.rollback()
        raise

def load_context(user_id: str, db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Load conversation context for a user
    """
    try:
        from app.models.chatbot import ChatbotConversation, ChatbotMessage
        
        # Find most recent active conversation
        conversation = db.query(ChatbotConversation).filter(
            ChatbotConversation.user_id == int(user_id) if user_id.isdigit() else 1,
            ChatbotConversation.is_active == True
        ).order_by(ChatbotConversation.last_activity.desc()).first()
        
        if not conversation:
            return []
        
        # Get recent messages
        messages = db.query(ChatbotMessage).filter(
            ChatbotMessage.conversation_id == conversation.id
        ).order_by(ChatbotMessage.created_at.desc()).limit(limit).all()
        
        # Convert to context format (reverse order for chronological)
        context = []
        for msg in reversed(messages):
            context.append({
                "role": msg.message_type,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat() if msg.created_at else None
            })
        
        logger.debug(f"Loaded {len(context)} context messages for user {user_id}")
        return context
        
    except Exception as e:
        logger.warning(f"Failed to load context for user {user_id}: {e}")
        return []

def clear_conversation(user_id: str, db: Session, conversation_id: Optional[str] = None):
    """
    Clear/close conversation for user
    """
    try:
        from app.models.chatbot import ChatbotConversation
        
        if conversation_id:
            # Close specific conversation
            conversation = db.query(ChatbotConversation).filter(
                ChatbotConversation.session_id == conversation_id
            ).first()
            if conversation:
                conversation.is_active = False
                db.commit()
                logger.info(f"Closed conversation {conversation_id}")
        else:
            # Close all active conversations for user
            conversations = db.query(ChatbotConversation).filter(
                ChatbotConversation.user_id == int(user_id) if user_id.isdigit() else 1,
                ChatbotConversation.is_active == True
            ).all()
            
            for conv in conversations:
                conv.is_active = False
            
            db.commit()
            logger.info(f"Closed {len(conversations)} conversations for user {user_id}")
            
    except Exception as e:
        logger.error(f"Failed to clear conversation: {e}")
        db.rollback()
        raise

def get_conversation_stats(user_id: str, db: Session) -> Dict[str, Any]:
    """
    Get conversation statistics for user
    """
    try:
        from app.models.chatbot import ChatbotConversation, ChatbotMessage
        from sqlalchemy import func
        
        user_id_int = int(user_id) if user_id.isdigit() else 1
        
        # Total conversations
        total_conversations = db.query(ChatbotConversation).filter(
            ChatbotConversation.user_id == user_id_int
        ).count()
        
        # Active conversations
        active_conversations = db.query(ChatbotConversation).filter(
            ChatbotConversation.user_id == user_id_int,
            ChatbotConversation.is_active == True
        ).count()
        
        # Total messages
        total_messages = db.query(ChatbotMessage).join(ChatbotConversation).filter(
            ChatbotConversation.user_id == user_id_int
        ).count()
        
        # Last activity
        last_conv = db.query(ChatbotConversation).filter(
            ChatbotConversation.user_id == user_id_int
        ).order_by(ChatbotConversation.last_activity.desc()).first()
        
        last_activity = last_conv.last_activity.isoformat() if last_conv and last_conv.last_activity else None
        
        return {
            "total_conversations": total_conversations,
            "active_conversations": active_conversations,
            "total_messages": total_messages,
            "last_activity": last_activity
        }
        
    except Exception as e:
        logger.warning(f"Failed to get conversation stats: {e}")
        return {
            "total_conversations": 0,
            "active_conversations": 0, 
            "total_messages": 0,
            "last_activity": None
        }

def cleanup_old_conversations(db: Session, days: int = 30):
    """
    Clean up old inactive conversations
    """
    try:
        from app.models.chatbot import ChatbotConversation, ChatbotMessage
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Find old inactive conversations
        old_conversations = db.query(ChatbotConversation).filter(
            ChatbotConversation.is_active == False,
            ChatbotConversation.last_activity < cutoff_date
        ).all()
        
        deleted_count = 0
        for conv in old_conversations:
            # Delete associated messages
            db.query(ChatbotMessage).filter(
                ChatbotMessage.conversation_id == conv.id
            ).delete()
            
            # Delete conversation
            db.delete(conv)
            deleted_count += 1
        
        db.commit()
        logger.info(f"Cleaned up {deleted_count} old conversations")
        
    except Exception as e:
        logger.error(f"Failed to cleanup old conversations: {e}")
        db.rollback()
