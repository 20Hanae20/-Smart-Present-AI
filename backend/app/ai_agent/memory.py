
import logging
from datetime import datetime
from typing import List, Dict, Any
from app.db.database import SessionLocal
from app.models.chatbot import ChatbotConversation, ChatbotMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Limite du nombre de messages à charger pour éviter les dépassements de tokens
MAX_CONTEXT_MESSAGES = 10

def save_turn(user_id, user_message, assistant_message):
    """
    Sauvegarde un échange (question + réponse) dans BOTH NTIC2 and SmartPresence databases
    
    Args:
        user_id: Identifiant de l'utilisateur (can be string or int)
        user_message: Message de l'utilisateur
        assistant_message: Réponse de l'assistant
    
    Returns:
        bool: True si la sauvegarde a réussi, False sinon
    """
    if not user_id or not user_message or not assistant_message:
        logger.warning(f"Tentative de sauvegarde avec des données invalides: user_id={user_id}, user_msg_len={len(user_message) if user_message else 0}, assistant_msg_len={len(assistant_message) if assistant_message else 0}")
        return False
    
    # Nettoyer les messages (enlever les caractères de contrôle)
    clean_user_msg = user_message.strip()[:10000]  # Limiter la taille
    clean_assistant_msg = assistant_message.strip()[:10000]
    
    # Convert user_id to int if it's a string
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        logger.error(f"Invalid user_id format: {user_id}")
        return False
    
    # Save to SmartPresence database using SQLAlchemy
    try:
        db = SessionLocal()
        try:
            # Get or create conversation
            conversation = db.query(ChatbotConversation).filter(
                ChatbotConversation.user_id == user_id_int
            ).first()
            
            if not conversation:
                conversation = ChatbotConversation(
                    user_id=user_id_int,
                    title=f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                db.add(conversation)
                db.flush()
            
            # Save user message
            user_msg_obj = ChatbotMessage(
                conversation_id=conversation.id,
                role="user",
                content=clean_user_msg
            )
            db.add(user_msg_obj)
            
            # Save assistant message
            assistant_msg_obj = ChatbotMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=clean_assistant_msg
            )
            db.add(assistant_msg_obj)
            
            db.commit()
            logger.info(f"✅ SmartPresence: Échange sauvegardé pour user_id: {user_id_int} (user: {len(clean_user_msg)} chars, assistant: {len(clean_assistant_msg)} chars)")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Erreur SmartPresence lors de la sauvegarde de l'échange: {e}")
        return False

def load_context(user_id, limit=MAX_CONTEXT_MESSAGES, max_tokens=None):
    """
    Charge le contexte conversationnel from BOTH NTIC2 and SmartPresence databases
    
    Args:
        user_id: Identifiant de l'utilisateur (can be string or int)
        limit: Nombre maximum d'échanges (user+assistant) à charger (défaut: 10)
        max_tokens: Limite optionnelle en tokens approximatifs (None = pas de limite)
    
    Returns:
        Liste de dictionnaires avec 'role' et 'content' pour chaque message
        Format compatible avec l'API OpenAI
    """
    # Convert user_id to int if it's a string
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        logger.error(f"Invalid user_id format: {user_id}")
        return []
    
    # Load from SmartPresence database using SQLAlchemy
    try:
        db = SessionLocal()
        try:
            # Get conversation for this user
            conversation = db.query(ChatbotConversation).filter(
                ChatbotConversation.user_id == user_id_int
            ).first()
            
            if not conversation:
                logger.info(f"No conversation found for user_id: {user_id_int}")
                return []
            
            # Load messages
            query_limit = limit * 2 if max_tokens is None else limit * 3
            messages = db.query(ChatbotMessage).filter(
                ChatbotMessage.conversation_id == conversation.id
            ).order_by(ChatbotMessage.created_at.desc()).limit(query_limit).all()
            
            if not messages:
                return []
            
            # Inverser pour avoir l'ordre chronologique (plus ancien en premier)
            messages = list(reversed(messages))
            
            # Formater en format OpenAI
            formatted_messages = []
            total_tokens_approx = 0
            
            for msg in messages:
                # Estimation approximative des tokens (1 token ≈ 4 caractères)
                msg_tokens = len(msg.content) // 4
                
                # Vérifier la limite de tokens si spécifiée
                if max_tokens is not None:
                    if total_tokens_approx + msg_tokens > max_tokens:
                        logger.info(f"Limite de tokens atteinte ({max_tokens}), arrêt du chargement")
                        break
                
                formatted_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
                
                total_tokens_approx += msg_tokens
                
                # Limiter aussi par nombre de messages
                if len(formatted_messages) >= limit * 2:
                    break
            
            logger.info(f"✅ SmartPresence: Contexte chargé: {len(formatted_messages)} messages (~{total_tokens_approx} tokens) pour user_id: {user_id_int}")
            return formatted_messages
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Erreur SmartPresence lors du chargement du contexte: {e}", exc_info=True)
        return []

def clear_conversation(user_id):
    """
    Efface l'historique de conversation BOTH in NTIC2 and SmartPresence databases
    
    Args:
        user_id: Identifiant de l'utilisateur (can be string or int)
    """
    # Convert user_id to int if it's a string
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        logger.error(f"Invalid user_id format: {user_id}")
        return
    
    # Clear from SmartPresence database using SQLAlchemy
    try:
        db = SessionLocal()
        try:
            # Get conversation
            conversation = db.query(ChatbotConversation).filter(
                ChatbotConversation.user_id == user_id_int
            ).first()
            
            if conversation:
                # Delete all messages in this conversation
                db.query(ChatbotMessage).filter(
                    ChatbotMessage.conversation_id == conversation.id
                ).delete()
                
                db.commit()
                logger.info(f"✅ SmartPresence: Historique effacé pour user_id: {user_id_int}")
            else:
                logger.info(f"No conversation to clear for user_id: {user_id_int}")
                
        finally:
            db.close()
            
    except Exception as e:
        logger.warning(f"❌ Erreur SmartPresence lors de l'effacement de l'historique: {e}")
