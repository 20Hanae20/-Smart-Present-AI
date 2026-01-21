"""
Smart Presence AI RAG Pipeline - EXACT NTIC2 Implementation
Vector search and document retrieval using ChromaDB
"""

import os
import logging
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

# Global variables for lazy loading
_embedding_function = None
_chroma_collection = None

def get_embedding_function():
    """
    Get embedding function with multiple fallback strategies
    1. sentence-transformers (local)
    2. OpenAI embeddings  
    3. Default fallback
    """
    global _embedding_function
    
    if _embedding_function:
        return _embedding_function
    
    try:
        # Try sentence-transformers first (local, free)
        from sentence_transformers import SentenceTransformer
        _embedding_function = SentenceTransformer('all-MiniLM-L6-v2').encode
        logger.info("Using sentence-transformers embeddings")
        return _embedding_function
    except ImportError:
        logger.warning("sentence-transformers not available")
    except Exception as e:
        logger.warning(f"sentence-transformers failed: {e}")
    
    try:
        # Try OpenAI embeddings
        import openai
        if os.getenv("OPENAI_API_KEY"):
            client = openai.OpenAI()
            
            def openai_embed(texts):
                if isinstance(texts, str):
                    texts = [texts]
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=texts
                )
                return [e.embedding for e in response.data]
            
            _embedding_function = openai_embed
            logger.info("Using OpenAI embeddings")
            return _embedding_function
    except Exception as e:
        logger.warning(f"OpenAI embeddings failed: {e}")
    
    # Default fallback - simple TF-IDF style
    logger.warning("Using fallback embedding function")
    def fallback_embed(texts):
        if isinstance(texts, str):
            texts = [texts]
        
        # Simple character-based embedding (not ideal but works)
        embeddings = []
        for text in texts:
            # Create simple fixed-size vector based on character frequencies
            import numpy as np
            chars = list(text.lower())
            freq = {}
            for char in chars:
                freq[char] = freq.get(char, 0) + 1
            
            # Create 384-dim vector (standard size)
            vec = np.zeros(384)
            for i, char in enumerate(chars[:384]):
                vec[i] = ord(char) / 255.0
            
            embeddings.append(vec.tolist())
        
        return embeddings
    
    _embedding_function = fallback_embed
    return _embedding_function

def get_chromadb_path() -> str:
    """Get ChromaDB storage path"""
    # Check if we're in Docker
    if os.path.exists("/app"):
        return "/app/chroma_db"
    
    # Local development
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(os.path.dirname(current_dir))
    return os.path.join(backend_dir, "chroma_db")

def init_collection(collection_name: str = "smartpresence_knowledge"):
    """
    Initialize ChromaDB collection
    """
    global _chroma_collection
    
    if _chroma_collection:
        return _chroma_collection
    
    try:
        chroma_path = get_chromadb_path()
        os.makedirs(chroma_path, exist_ok=True)
        
        client = chromadb.PersistentClient(path=chroma_path)
        embedding_func = get_embedding_function()
        
        # Create or get collection
        try:
            _chroma_collection = client.get_collection(name=collection_name)
            logger.info(f"Loaded existing collection: {collection_name}")
        except Exception:
            _chroma_collection = client.create_collection(
                name=collection_name,
                embedding_function=embedding_func
            )
            logger.info(f"Created new collection: {collection_name}")
        
        return _chroma_collection
        
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB: {e}")
        raise

def seed_smartpresence_knowledge():
    """
    Seed ChromaDB with Smart Presence knowledge base
    """
    try:
        collection = init_collection()
        
        # Check if already seeded
        try:
            count = collection.count()
            if count > 0:
                logger.info(f"Collection already has {count} documents")
                return
        except:
            pass
        
        # Smart Presence knowledge documents
        documents = [
            {
                "id": "checkin_procedure",
                "text": "Pour faire le check-in avec Smart Presence AI: 1) Connectez-vous à votre compte 2) Allez dans la section 'Présences' 3) Cliquez sur 'Check-in' 4) Choisissez la méthode: reconnaissance faciale ou code QR 5) Pour la reconnaissance faciale, positionnez votre visage dans le cadre 6) Attendez la validation verte 7) Votre présence est enregistrée automatiquement",
                "metadata": {"category": "procedures", "topic": "checkin"}
            },
            {
                "id": "checkout_procedure", 
                "text": "Pour faire le check-out: 1) Allez dans 'Présences' 2) Cliquez sur 'Check-out' 3) Utilisez la même méthode que le check-in 4) Confirmez votre départ 5) La durée de présence est calculée automatiquement 6) Vous recevez une confirmation de check-out",
                "metadata": {"category": "procedures", "topic": "checkout"}
            },
            {
                "id": "facial_recognition",
                "text": "La reconnaissance faciale de Smart Presence: 1) Enregistrement initial requis avec photo claire 2) Vérification de vivacité (liveness detection) 3) Correspondance vectorielle avec base de données 4) Seuil de confiance de 60% minimum 5) Stockage sécurisé des embeddings faciaux 6) Possibilité de refaire la photo si mauvaise qualité",
                "metadata": {"category": "features", "topic": "facial_recognition"}
            },
            {
                "id": "absence_justification",
                "text": "Pour justifier une absence: 1) Connectez-vous à votre espace 2) Allez dans 'Historique des présences' 3) Cliquez sur l'absence concernée 4) Cliquez sur 'Justifier' 5) Rédigez votre justification 6) Joignez des documents si nécessaire (certificat médical, etc.) 7) Soumettez pour validation 8) Le formateur sera notifié",
                "metadata": {"category": "procedures", "topic": "justification"}
            },
            {
                "id": "qr_checkin",
                "text": "Check-in par code QR: 1) Le formateur génère un QR code unique pour la session 2) Le QR code est valide 15 minutes 3) Scannez le QR avec votre appareil photo 4) Le système valide automatiquement votre présence 5) Alternative si reconnaissance faciale indisponible 6. Historique conservé dans votre profil",
                "metadata": {"category": "features", "topic": "qr_code"}
            },
            {
                "id": "dashboard_features",
                "text": "Tableau de bord Smart Presence: 1) Vue d'ensemble des présences/absences 2) Statistiques en temps réel 3) Graphiques de fréquentation 4) Notifications importantes 5) Accès rapide aux fonctionnalités 6) Export des données (PDF/CSV) 7) Filtrage par date et session 8) Vue calendrier des sessions",
                "metadata": {"category": "features", "topic": "dashboard"}
            },
            {
                "id": "troubleshooting",
                "text": "Problèmes courants et solutions: 1) Reconnaissance faciale échoue: vérifiez l'éclairage, centrez votre visage 2) QR code invalide: demandez un nouveau code au formateur 3) Check-in impossible: vérifiez votre connexion internet 4) Photo non acceptée: assurez-vous que le visage est visible et net 5) Session non trouvée: vérifiez le code de session avec le formateur",
                "metadata": {"category": "support", "topic": "troubleshooting"}
            }
        ]
        
        # Add documents to collection
        for doc in documents:
            try:
                collection.add(
                    ids=[doc["id"]],
                    documents=[doc["text"]],
                    metadatas=[doc["metadata"]]
                )
            except Exception as e:
                logger.warning(f"Failed to add document {doc['id']}: {e}")
        
        logger.info(f"Seeded {len(documents)} knowledge documents")
        
    except Exception as e:
        logger.error(f"Failed to seed knowledge: {e}")

def rag_answer(query: str, n_results: int = 3) -> Optional[Dict[str, Any]]:
    """
    Perform RAG search to find relevant documents
    """
    try:
        collection = init_collection()
        
        # Search for relevant documents
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        if not results or not results["documents"][0]:
            return None
        
        # Filter results by distance threshold (remove irrelevant results)
        threshold = 1.5
        filtered_docs = []
        filtered_sources = []
        
        for i, distance in enumerate(results["distances"][0]):
            if distance <= threshold:
                doc_text = results["documents"][0][i]
                metadata = results["metadatas"][0][i]
                
                filtered_docs.append(doc_text)
                filtered_sources.append({
                    "text": doc_text[:100] + "...",
                    "metadata": metadata,
                    "distance": distance
                })
        
        if not filtered_docs:
            return None
        
        # Combine relevant documents
        combined_context = "\n\n".join(filtered_docs)
        
        return {
            "answer": combined_context,
            "sources": filtered_sources,
            "query": query,
            "found_documents": len(filtered_docs)
        }
        
    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        return None
