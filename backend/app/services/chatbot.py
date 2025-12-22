import json
from datetime import datetime
from typing import Optional, Dict, Any, Iterator

from sqlalchemy.orm import Session

from app.models.chatbot import ChatbotConversation, ChatbotMessage
from app.services.gemini_service import GeminiService
from app.ai_agent.core import agent_run_streaming  # EXACT NTIC2: function-based approach
from app.ai_agent.memory import load_context  # EXACT NTIC2: conversation history
import logging

logger = logging.getLogger(__name__)


class ChatbotService:
    """
    Enhanced service layer for chatbot with AI Agent integration.
    Supports both legacy FAQ fallback and advanced RAG-powered responses.
    """

    # Simple FAQ knowledge base (fallback only)
    FAQ = {
        "horaires": {
            "keywords": ["horaire", "heure", "temps", "quand", "timing", "schedule"],
            "response": "Les horaires des cours sont affichés dans votre emploi du temps personnel. Veuillez consulter l'onglet 'Emploi du temps'.",
        },
        "absences": {
            "keywords": ["absence", "absent", "manqué", "skip"],
            "response": "Vous pouvez consulter vos absences dans l'onglet 'Présences'. Si vous avez une justification, veuillez la soumettre.",
        },
        "justification": {
            "keywords": ["justification", "justifier", "document", "preuve"],
            "response": "Pour justifier une absence, allez dans 'Présences' et cliquez sur l'absence concernée. Vous pouvez ajouter une justification et des documents.",
        },
        "examen": {
            "keywords": ["examen", "exam", "test", "partiel"],
            "response": "Les dates et heures des examens sont dans votre emploi du temps. Vous recevrez un rappel 24 heures avant.",
        },
        "note": {
            "keywords": ["note", "score", "résultat", "note", "grade"],
            "response": "Les résultats d'examen seront disponibles 3 jours après l'examen. Consultez la section 'Résultats'.",
        },
        "contact": {
            "keywords": ["contact", "formateur", "trainer", "professeur", "mail"],
            "response": "Vous pouvez contacter votre formateur via l'onglet 'Contacts' ou par email indiqué dans votre profil.",
        },
        "notifications": {
            "keywords": ["notification", "notifications", "alerte", "alertes", "notify", "bell"],
            "response": "Vos notifications récentes sont visibles dans l'onglet 'Notifications'. Vous pouvez activer/désactiver les alertes dans les paramètres.",
        },
        "salut": {
            "keywords": ["bonjour", "salut", "hello", "hi"],
            "response": "Bonjour ! Comment puis-je vous aider ? Vous pouvez me demander vos horaires, absences, justifications, examens, notes ou contacts.",
        },
    }

    @staticmethod
    def start_conversation(db: Session, user_id: int, user_type: str) -> ChatbotConversation:
        """Start a new chatbot conversation."""
        conversation = ChatbotConversation(
            user_id=user_id,
            user_type=user_type,
            session_id=f"{user_id}_{datetime.now().timestamp()}",
            context_data=json.dumps({}),
            conversation_history=json.dumps([]),
            is_active=True,
            message_count=0,
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def send_message(db: Session, conversation_id: int, user_message: str, user_id: int = None) -> ChatbotMessage:
        """Process user message and return assistant response using AI Agent."""
        conversation = (
            db.query(ChatbotConversation).filter(ChatbotConversation.id == conversation_id).first()
        )
        if not conversation:
            return None

        # Store user message
        user_msg = ChatbotMessage(
            conversation_id=conversation_id,
            message_type="user",
            content=user_message,
        )
        db.add(user_msg)

        # Build user context for AI Agent
        user_context = {
            "role": conversation.user_type,
            "user_id": user_id or conversation.user_id,
        }

        # Generate assistant response with AI Agent
        response_data = ChatbotService.generate_response(user_message, user_context, db, conversation_id)
        response_text = response_data.get("reply", "Je n'ai pas pu générer une réponse.")
        intent = ChatbotService.detect_intent(user_message)

        # Store sources in metadata
        sources = response_data.get("sources", [])
        entities_extracted = {
            "rag_used": response_data.get("rag_used", False),
            "sources": sources,
            "language": response_data.get("language", "fr")
        }

        assistant_msg = ChatbotMessage(
            conversation_id=conversation_id,
            message_type="assistant",
            content=response_text,
            intent_detected=intent,
            confidence_score=0.85,
            entities_extracted=entities_extracted,
        )
        db.add(assistant_msg)

        # Update conversation
        conversation.message_count += 1
        conversation.last_activity = datetime.now()

        db.commit()
        db.refresh(assistant_msg)
        return assistant_msg

    @staticmethod
    def generate_response(
        user_message: str, 
        user_context: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
        conversation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate chatbot response using AI Agent (EXACT NTIC2 approach).
        Falls back to Gemini, then FAQ if AI Agent fails.
        """
        try:
            # Get user_id from context
            user_id = user_context.get("user_id", 1) if user_context else 1
            
            # EXACT NTIC2: Direct function call with only message and user_id
            # agent_run_streaming handles RAG, multi-provider LLM, and caching internally
            response_generator = agent_run_streaming(
                message=user_message,
                user_id=str(user_id)  # NTIC2 expects string user_id
            )
            
            # Collect response from generator (NTIC2 yields JSON strings)
            full_response = ""
            sources = []
            for chunk_str in response_generator:
                try:
                    # Parse JSON string (EXACT NTIC2 format)
                    chunk = json.loads(chunk_str) if isinstance(chunk_str, str) else chunk_str
                    # NTIC2 uses "type": "content" not "token"
                    if chunk.get("type") == "content":
                        full_response += chunk.get("content", "")
                    elif chunk.get("type") == "sources":
                        sources = chunk.get("sources", [])
                except (json.JSONDecodeError, AttributeError):
                    # If not JSON, treat as raw text token
                    full_response += str(chunk_str)
            
            if full_response:
                return {
                    "reply": full_response,
                    "sources": sources,
                    "rag_used": len(sources) > 0,
                    "language": "fr",
                    "provider": "ai_agent"
                }
            
            logger.warning("AI Agent returned empty response, falling back")
            
        except Exception as e:
            logger.error(f"AI Agent error: {e}", exc_info=True)
        
        # Fallback 1: Try Gemini (legacy)
        try:
            gemini_service = GeminiService()
            response_text = gemini_service.generate_response(user_message, user_context)
            
            if response_text and not response_text.startswith("Error"):
                return {
                    "reply": response_text,
                    "sources": [],
                    "rag_used": False,
                    "language": "fr",
                    "provider": "gemini"
                }
        except Exception as e:
            logger.error(f"Gemini fallback error: {e}")
        
        # Fallback 2: FAQ-based response (last resort)
        faq_response = ChatbotService._generate_faq_response(user_message)
        return {
            "reply": faq_response,
            "sources": [],
            "rag_used": False,
            "language": "fr",
            "provider": "faq"
        }

    @staticmethod
    def _generate_faq_response(user_message: str) -> str:
        """Generate response based on FAQ knowledge base (fallback)."""
        user_lower = user_message.lower()

        # Check each FAQ category
        for category, data in ChatbotService.FAQ.items():
            for keyword in data["keywords"]:
                if keyword in user_lower:
                    return data["response"]

        # Default response
        return "Je n'ai pas bien compris. Pouvez-vous reformuler votre question ? (Tapez: horaires, absences, justification, examen, note, contact)"

    @staticmethod
    def detect_intent(user_message: str) -> str:
        """Detect intent from user message."""
        user_lower = user_message.lower()

        for category, data in ChatbotService.FAQ.items():
            for keyword in data["keywords"]:
                if keyword in user_lower:
                    return category

        return "general"

    @staticmethod
    def get_conversation_history(db: Session, conversation_id: int, limit: int = 50):
        """Get conversation history."""
        messages = (
            db.query(ChatbotMessage)
            .filter(ChatbotMessage.conversation_id == conversation_id)
            .order_by(ChatbotMessage.created_at.asc())
            .limit(limit)
            .all()
        )
        return messages

    @staticmethod
    def close_conversation(db: Session, conversation_id: int):
        """Close a conversation."""
        conversation = (
            db.query(ChatbotConversation).filter(ChatbotConversation.id == conversation_id).first()
        )
        if conversation:
            conversation.is_active = False
            db.commit()
            db.refresh(conversation)
        return conversation

    @staticmethod
    def set_satisfaction_score(db: Session, conversation_id: int, score: int, feedback: str = None):
        """Set user satisfaction with chatbot."""
        conversation = (
            db.query(ChatbotConversation).filter(ChatbotConversation.id == conversation_id).first()
        )
        if conversation:
            conversation.user_satisfaction_score = score
            conversation.feedback_text = feedback
            db.commit()
            db.refresh(conversation)
        return conversation

    @staticmethod
    def generate_response_streaming(
        user_message: str,
        user_context: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
        conversation_id: Optional[int] = None
    ) -> Iterator[str]:
        """
        Generate streaming response using AI Agent.
        Yields JSON chunks for real-time updates.
        """
        try:
            agent = AgentCore(db=db)
            user_id = user_context.get("user_id", 1) if user_context else 1
            
            for chunk in agent.generate_response_streaming(
                message=user_message,
                user_id=user_id,
                conversation_id=conversation_id,
                user_context=user_context
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield json.dumps({
                "type": "error",
                "message": f"Erreur de streaming: {str(e)}"
            })
