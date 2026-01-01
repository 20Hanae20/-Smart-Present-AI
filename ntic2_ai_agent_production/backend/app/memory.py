
import logging
from app.db.database import query_db, get_db_connection
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Limite du nombre de messages à charger pour éviter les dépassements de tokens
MAX_CONTEXT_MESSAGES = 10

def save_turn(user_id, user_message, assistant_message):
    """
    Sauvegarde un échange (question + réponse) dans la base de données
    
    Args:
        user_id: Identifiant de l'utilisateur
        user_message: Message de l'utilisateur
        assistant_message: Réponse de l'assistant
    
    Returns:
        bool: True si la sauvegarde a réussi, False sinon
    """
    if not user_id or not user_message or not assistant_message:
        logger.warning(f"Tentative de sauvegarde avec des données invalides: user_id={user_id}, user_msg_len={len(user_message) if user_message else 0}, assistant_msg_len={len(assistant_message) if assistant_message else 0}")
        return False
    
    try:
        conn = get_db_connection()
        if conn is None:
            return False
            
        cur = conn.cursor()
        
        # Nettoyer les messages (enlever les caractères de contrôle)
        clean_user_msg = user_message.strip()[:10000]  # Limiter la taille
        clean_assistant_msg = assistant_message.strip()[:10000]
        
        cur.execute(
            "INSERT INTO conversation_history (user_id, user_message, assistant_message) VALUES (%s, %s, %s)",
            (user_id, clean_user_msg, clean_assistant_msg)
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Échange sauvegardé pour user_id: {user_id} (user: {len(clean_user_msg)} chars, assistant: {len(clean_assistant_msg)} chars)")
        return True
        
    except Exception as e:
        # Ne pas logger comme erreur si c'est juste PostgreSQL qui n'est pas accessible
        error_msg = str(e).lower()
        if "connection refused" in error_msg or "postgresql non accessible" in error_msg or "none" in error_msg:
            logger.warning(f"PostgreSQL non accessible, sauvegarde ignorée")
        else:
            logger.error(f"Erreur lors de la sauvegarde de l'echange: {e}")
        return False

def load_context(user_id, limit=MAX_CONTEXT_MESSAGES, max_tokens=None):
    """
    Charge le contexte conversationnel (les N derniers échanges)
    
    Args:
        user_id: Identifiant de l'utilisateur
        limit: Nombre maximum d'échanges (user+assistant) à charger (défaut: 10)
        max_tokens: Limite optionnelle en tokens approximatifs (None = pas de limite)
    
    Returns:
        Liste de dictionnaires avec 'role' et 'content' pour chaque message
        Format compatible avec l'API OpenAI
    """
    try:
        # Charger plus de messages si on a une limite de tokens
        query_limit = limit * 2 if max_tokens is None else limit * 3
        
        messages = query_db(
            "SELECT user_message, assistant_message, created_at FROM conversation_history WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
            (user_id, query_limit)
        )
        
        if not messages:
            return []
        
        # Inverser pour avoir l'ordre chronologique (plus ancien en premier)
        messages = list(reversed(messages))
        
        # Formater en format OpenAI (alternance user/assistant)
        formatted_messages = []
        total_tokens_approx = 0
        
        for msg in messages:
            user_msg = msg['user_message']
            assistant_msg = msg['assistant_message']
            
            # Estimation approximative des tokens (1 token ≈ 4 caractères)
            user_tokens = len(user_msg) // 4
            assistant_tokens = len(assistant_msg) // 4
            
            # Vérifier la limite de tokens si spécifiée
            if max_tokens is not None:
                if total_tokens_approx + user_tokens + assistant_tokens > max_tokens:
                    logger.info(f"Limite de tokens atteinte ({max_tokens}), arrêt du chargement")
                    break
            
            formatted_messages.append({
                "role": "user",
                "content": user_msg
            })
            formatted_messages.append({
                "role": "assistant",
                "content": assistant_msg
            })
            
            total_tokens_approx += user_tokens + assistant_tokens
            
            # Limiter aussi par nombre d'échanges
            if len(formatted_messages) >= limit * 2:
                break
        
        logger.info(f"Contexte chargé: {len(formatted_messages)} messages ({len(formatted_messages)//2} échanges, ~{total_tokens_approx} tokens) pour user_id: {user_id}")
        return formatted_messages
        
    except Exception as e:
        # Ne pas logger comme erreur si c'est juste PostgreSQL qui n'est pas accessible
        error_msg = str(e).lower()
        if "connection refused" in error_msg or "postgresql non accessible" in error_msg:
            logger.warning(f"PostgreSQL non accessible, historique vide: {e}")
        else:
            logger.error(f"Erreur lors du chargement du contexte: {e}", exc_info=True)
        return []

def clear_conversation(user_id):
    """
    Efface l'historique de conversation pour un utilisateur
    
    Args:
        user_id: Identifiant de l'utilisateur
    """
    try:
        conn = get_db_connection()
        if conn is None:
            return
            
        cur = conn.cursor()
        
        cur.execute(
            "DELETE FROM conversation_history WHERE user_id = %s",
            (user_id,)
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Historique effacé pour user_id: {user_id}")
        
    except Exception as e:
        logger.warning(f"Erreur lors de l'effacement de l'historique: {e}")
