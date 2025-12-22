
import os
import time
import chromadb  # pyright: ignore[reportMissingImports]
from chromadb.utils import embedding_functions  # pyright: ignore[reportMissingImports]
import logging
from dotenv import load_dotenv
from pathlib import Path

# Charger les variables d'environnement depuis .env à la racine du projet
# (au cas où ce module serait importé directement sans passer par main.py)
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

def get_chromadb_path():
    """Retourne le chemin ChromaDB adapté à l'environnement (Docker ou local)"""
    if os.path.exists("/app"):
        # Environnement Docker
        return "/app/chroma_db"
    else:
        # Environnement local
        # Remonter depuis backend/app/rag/pipeline.py vers la racine du projet
        # backend/app/rag/pipeline.py -> backend/app/rag -> backend/app -> backend -> racine
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # backend/app/rag -> backend/app -> backend -> racine
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        chroma_db_path = os.path.join(root_dir, "chroma_db")
        os.makedirs(chroma_db_path, exist_ok=True)
        return chroma_db_path

# Imports pour embeddings locaux (lazy loading pour éviter les problèmes de mémoire)
SENTENCE_TRANSFORMERS_AVAILABLE = False
_SentenceTransformer = None
_embedding_model = None

# Cache pour les embeddings (optimisation performance) - LRU Cache inspiré de repochat
from collections import OrderedDict
_embedding_cache = OrderedDict()
_cache_max_size = 1000

def _get_hf_embedding_function():
    """Crée une fonction d'embedding utilisant l'API Hugging Face (gratuite)"""
    try:
        import requests
        
        class HuggingFaceEmbeddingFunction:
            """Fonction d'embedding utilisant l'API Hugging Face Inference (gratuite)"""
            def __init__(self):
                # Utiliser la nouvelle URL router.huggingface.co
                self.api_url = "https://router.huggingface.co/pipeline/feature-extraction/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
                self.headers = {"Authorization": f"Bearer {os.environ.get('HF_API_KEY', '')}"} if os.environ.get('HF_API_KEY') else {}
            
            def name(self):
                """Retourne le nom de la fonction d'embedding (requis par ChromaDB)"""
                return "huggingface-api"
            
            def embed_query(self, input):
                """Méthode pour les requêtes (compatible ChromaDB)"""
                return self(input)
            
            def __call__(self, input):
                """Génère les embeddings via l'API Hugging Face"""
                if isinstance(input, str):
                    input = [input]
                
                try:
                    # Utiliser l'API Hugging Face (gratuite, pas de quota)
                    response = requests.post(
                        self.api_url,
                        headers=self.headers,
                        json={"inputs": input},
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        embeddings = response.json()
                        # S'assurer que c'est une liste de listes
                        if isinstance(embeddings, list) and len(embeddings) > 0:
                            if isinstance(embeddings[0], list):
                                return embeddings
                            else:
                                return [embeddings]
                        return embeddings
                    else:
                        logger.warning(f"Erreur API Hugging Face: {response.status_code}, fallback vers OpenAI")
                        raise Exception(f"HF API error: {response.status_code}")
                except Exception as e:
                    logger.warning(f"Erreur avec Hugging Face API: {e}, fallback vers OpenAI")
                    raise
        
        return HuggingFaceEmbeddingFunction()
    except Exception as e:
        logger.warning(f"Impossible de créer la fonction Hugging Face: {e}")
        return None

def _get_sentence_transformer():
    """Import lazy de SentenceTransformer pour éviter les blocages au démarrage"""
    global SENTENCE_TRANSFORMERS_AVAILABLE, _SentenceTransformer
    if _SentenceTransformer is None:
        try:
            from sentence_transformers import SentenceTransformer  # pyright: ignore[reportMissingImports]
            _SentenceTransformer = SentenceTransformer
            SENTENCE_TRANSFORMERS_AVAILABLE = True
        except (ImportError, Exception) as e:
            logger.debug(f"sentence-transformers non disponible: {e}")
            SENTENCE_TRANSFORMERS_AVAILABLE = False
            _SentenceTransformer = False
    return _SentenceTransformer if SENTENCE_TRANSFORMERS_AVAILABLE else None

def get_embedding_model():
    """Charge le modèle d'embedding une seule fois (singleton)"""
    global _embedding_model
    if _embedding_model is None:
        SentenceTransformer = _get_sentence_transformer()
        if SentenceTransformer is not None:
            try:
                _embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            except Exception as e:
                logger.warning(f"Erreur lors du chargement du modèle sentence-transformers: {e}")
                _embedding_model = False
        else:
            _embedding_model = False
    return _embedding_model if _embedding_model is not False else None

def _get_ollama_embedding_function():
    """Crée une fonction d'embedding utilisant Ollama (fallback si autres échouent)"""
    try:
        import requests
        # Déterminer l'URL Ollama selon l'environnement
        if os.path.exists("/app"):
            # Docker
            ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
            if "host.docker.internal" in ollama_url:
                ollama_url = "http://ollama:11434"
        else:
            # Local : utiliser localhost
            ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            if "ollama:" in ollama_url or "host.docker.internal" in ollama_url:
                ollama_url = "http://localhost:11434"
        
        class OllamaEmbeddingFunction:
            """Fonction d'embedding utilisant Ollama"""
            def __init__(self):
                self.api_url = f"{ollama_url}/api/embeddings"
                self.model = "llama3.2:1b"  # Modèle avec support embeddings
            
            def name(self):
                return "ollama"
            
            def embed_query(self, input):
                """Méthode pour les requêtes (compatible ChromaDB)"""
                return self(input)
            
            def __call__(self, input):
                """Génère les embeddings via Ollama"""
                if isinstance(input, str):
                    input = [input]
                
                embeddings = []
                for text in input:
                    try:
                        response = requests.post(
                            self.api_url,
                            json={"model": self.model, "prompt": text},
                            timeout=180  # Timeout très long pour le chargement du modèle (3 minutes)
                        )
                        if response.status_code == 200:
                            result = response.json()
                            embedding = result.get("embedding", [])
                            if embedding and isinstance(embedding, list):
                                embeddings.append(embedding)
                            else:
                                logger.warning(f"Format embedding Ollama incorrect: {type(embedding)}")
                                # Retourner un embedding de dimension 3072 (taille du modèle) rempli de zéros
                                embeddings.append([0.0] * 3072)
                        else:
                            error_text = response.text[:200] if hasattr(response, 'text') else str(response.status_code)
                            logger.warning(f"Erreur Ollama embeddings: {response.status_code} - {error_text}")
                            # Retourner un embedding de dimension 3072 rempli de zéros comme fallback
                            embeddings.append([0.0] * 3072)
                    except requests.exceptions.Timeout:
                        logger.warning(f"Timeout Ollama embeddings (modèle en chargement)")
                        # Retourner un embedding de dimension 3072 rempli de zéros
                        embeddings.append([0.0] * 3072)
                    except Exception as e:
                        logger.warning(f"Erreur avec Ollama embeddings: {e}")
                        # Retourner un embedding de dimension 3072 rempli de zéros
                        embeddings.append([0.0] * 3072)
                
                # Toujours retourner une liste de listes
                if len(embeddings) == 1:
                    return embeddings
                return embeddings
        
        return OllamaEmbeddingFunction()
    except Exception as e:
        logger.warning(f"Impossible de créer la fonction Ollama embeddings: {e}")
        return None

def _get_cached_embedding(text, embedding_func):
    """Récupère un embedding depuis le cache LRU ou le calcule si absent (optimisé repochat)"""
    global _embedding_cache
    
    try:
        # Créer une clé de cache (normaliser le texte)
        cache_key = text.lower().strip()
        
        # Vérifier le cache (LRU: déplacer à la fin si trouvé)
        if cache_key in _embedding_cache:
            # Déplacer à la fin (most recently used)
            _embedding_cache.move_to_end(cache_key)
            logger.debug(f"✅ Embedding récupéré du cache LRU pour: {cache_key[:50]}...")
            return _embedding_cache[cache_key]
        
        # Calculer l'embedding
        embedding = embedding_func([text])
        if embedding and len(embedding) > 0:
            result = embedding[0] if isinstance(embedding[0], list) else embedding
            
            # Ajouter au cache (LRU: ajouter à la fin)
            if len(_embedding_cache) >= _cache_max_size:
                # Supprimer le plus ancien (LRU: premier élément)
                _embedding_cache.popitem(last=False)
            
            _embedding_cache[cache_key] = result
            # S'assurer que c'est à la fin (most recently used)
            _embedding_cache.move_to_end(cache_key)
            logger.debug(f"💾 Embedding calculé et mis en cache LRU: {cache_key[:50]}...")
            return result
        else:
            logger.warning(f"Embedding vide pour: {cache_key[:50]}...")
            return None
    except Exception as e:
        logger.error(f"Erreur lors du calcul de l'embedding: {e}", exc_info=True)
        # En cas d'erreur, essayer sans cache
        try:
            embedding = embedding_func([text])
            if embedding and len(embedding) > 0:
                return embedding[0] if isinstance(embedding[0], list) else embedding
        except:
            pass
        return None

def _get_dummy_embedding_function():
    """Fonction d'embedding de secours (retourne des zéros) pour éviter les crashs"""
    class DummyEmbeddingFunction:
        def name(self): return "dummy"
        def embed_query(self, input): return self(input)
        def __call__(self, input):
            if isinstance(input, str): input = [input]
            return [[0.0] * 384] * len(input) # Dimension standard pour MiniLM
    return DummyEmbeddingFunction()

def get_embedding_function():
    """Retourne la fonction d'embedding à utiliser avec cache intégré et timeouts"""
    # 1. Tenter sentence-transformers local (PRIORITÉ: le plus fiable et rapide)
    embedding_model = get_embedding_model()
    if embedding_model is not None:
        try:
            class CachedLocalEmbeddingFunction:
                def __init__(self, model):
                    self.model = model
                def name(self):
                    return "sentence-transformers"
                def embed_query(self, input): return self(input)
                def __call__(self, input):
                    if isinstance(input, str): input = [input]
                    # OPTIMISATION REPOCHAT: Batch processing pour meilleures performances
                    # Séparer les textes en cache et non-cache
                    cached_results = []
                    uncached_texts = []
                    uncached_indices = []
                    
                    for i, text in enumerate(input):
                        cached = _get_cached_embedding(text, self._compute_embedding)
                        if cached:
                            cached_results.append((i, cached))
                        else:
                            uncached_texts.append(text)
                            uncached_indices.append(i)
                    
                    # Traiter les non-cachés en batch (plus rapide)
                    if uncached_texts:
                        try:
                            batch_embeddings = self.model.encode(
                                uncached_texts, 
                                show_progress_bar=False, 
                                convert_to_numpy=True,
                                batch_size=min(32, len(uncached_texts))  # Batch size optimisé
                            )
                            for idx, embedding in zip(uncached_indices, batch_embeddings):
                                cached_results.append((idx, embedding.tolist()))
                        except Exception as e:
                            logger.warning(f"Erreur batch encoding: {e}, fallback séquentiel")
                            # Fallback séquentiel si batch échoue
                            for text in uncached_texts:
                                try:
                                    embedding = self.model.encode([text], show_progress_bar=False, convert_to_numpy=True)
                                    cached_results.append((len(cached_results), embedding[0].tolist()))
                                except: pass
                    
                    # Réordonner selon l'ordre original
                    cached_results.sort(key=lambda x: x[0])
                    results = [emb for _, emb in cached_results]
                    
                    # IMPORTANT: ChromaDB attend toujours une liste d'embeddings (liste de listes)
                    final_results = []
                    for res in results:
                        if isinstance(res, list):
                            final_results.append(res)
                        elif hasattr(res, 'tolist'):
                            final_results.append(res.tolist())
                        else:
                            final_results.append(list(res))
                    return final_results
                def _compute_embedding(self, input):
                    if isinstance(input, str): input = [input]
                    embeddings = self.model.encode(input, show_progress_bar=False, convert_to_numpy=True)
                    return embeddings.tolist()
            
            logger.info("✅ Embeddings: sentence-transformers local")
            return CachedLocalEmbeddingFunction(embedding_model)
        except Exception as e:
            logger.warning(f"⚠️ Erreur sentence-transformers: {e}")

    # 2. Tenter Hugging Face API (fallback gratuit)
    hf_ef = _get_hf_embedding_function()
    if hf_ef:
        try:
            # Test rapide
            hf_ef(["test"])
            logger.info("✅ Embeddings: Hugging Face API")
            return hf_ef
        except: pass

    # 3. Tenter Ollama
    ollama_ef = _get_ollama_embedding_function()
    if ollama_ef:
        logger.info("✅ Embeddings: Ollama (fallback)")
        return ollama_ef

    # 4. Dernier recours: Dummy
    logger.error("❌ AUCUNE FONCTION D'EMBEDDING DISPONIBLE. Utilisation du mode dégradé.")
    return _get_dummy_embedding_function()

def rag_answer(query, context=None, n_results=3, filter_section=None):
    """
    Recherche RAG ultra-rapide optimisée pour temps de réponse ≤ 2 secondes
    
    IMPORTANT - SYSTÈME D'EMBEDDINGS :
    - Les embeddings des documents sont calculés UNE SEULE FOIS lors de l'ingestion
    - ChromaDB stocke les embeddings de manière persistante sur disque
    - La base vectorielle est chargée depuis le disque à chaque requête (rapide)
    - Seul l'embedding de la question utilisateur est calculé à chaque requête
    - Les embeddings des documents ne sont JAMAIS recalculés
    
    Args:
        query: La question de l'utilisateur
        context: Contexte additionnel (non utilisé pour l'instant)
        n_results: Nombre de résultats à retourner (3-4 recommandé pour rapidité)
        filter_section: Filtrer par section si spécifié (ex: "emplois du temps")
    
    Returns:
        Tuple (contexte RAG formaté, liste des sources)
    """
    try:
        # ChromaDB PersistentClient charge la base vectorielle depuis le disque
        # Les embeddings des documents sont déjà stockés, pas besoin de les recalculer
        client = chromadb.PersistentClient(path=get_chromadb_path())
        
        # get_embedding_function() retourne la fonction pour calculer l'embedding de la QUESTION uniquement
        # Cette fonction est utilisée pour la recherche, pas pour recalculer les embeddings des documents
        embedding_function = get_embedding_function()
        
        # Vérifier si la collection existe, sinon retourner vide
        # La collection contient déjà tous les embeddings des documents calculés lors de l'ingestion
        try:
            collection = client.get_collection(name="website_content", embedding_function=embedding_function)
        except Exception as e:
            logger.warning(f"Collection 'website_content' n'existe pas encore. Exécutez d'abord le script d'ingestion: docker-compose exec backend python -m app.rag.ingest")
            return "", []
        
        # Vérifier si la collection est vide
        try:
            collection_data = collection.get()
            if not collection_data.get("ids") or len(collection_data["ids"]) == 0:
                logger.warning("Collection 'website_content' est vide. L'ingestion n'a pas été effectuée. Exécutez: docker-compose exec backend python -m app.rag.ingest")
                return "", []
        except Exception as e:
            logger.warning(f"Erreur lors de la vérification de la collection: {e}")
            return "", []
        
        # Construire les filtres si une section est spécifiée (mais ne pas être trop strict)
        where_clause = None
        if filter_section:
            # Normaliser la section pour la recherche (enlever espaces, convertir en minuscules)
            filter_section_normalized = filter_section.lower().replace(" ", "-").replace("_", "-")
            # Ne pas filtrer par section si elle est trop générique, mais plutôt chercher dans les résultats
            # On va faire une requête sans filtre et filtrer après selon la pertinence
            logger.info(f"Section détectée: {filter_section}, recherche sans filtre strict pour plus de résultats")
        
        # OPTIMISATION REPOCHAT: Pré-filtrage intelligent avant recherche vectorielle
        # Extraire les mots-clés de la requête pour pré-filtrage
        query_lower = query.lower()
        query_words = set([w for w in query_lower.split() if len(w) > 2])  # Mots de plus de 2 caractères
        
        # OPTIMISATION ULTRA-RAPIDE: topK=3 maximum (max 4) pour temps de réponse ≤ 1-2s
        # Le cache des embeddings accélère les requêtes répétées
        # IMPORTANT: Embeddings des documents calculés UNE SEULE FOIS lors de l'ingestion
        start_embed = time.time()
        
        # Augmenter légèrement n_results pour compenser le pré-filtrage
        query_n_results = min(n_results * 2, 6)  # Prendre 2x plus de résultats pour post-filtrage
        
        # OBTENIR L'EMBEDDING DE LA REQUÊTE MANUELLEMENT (plus robuste)
        try:
            embedding_function = get_embedding_function()
            if embedding_function:
                query_embeddings = embedding_function([query])
                # S'assurer que query_embeddings est une liste de listes (Sequence of Sequences)
                if not isinstance(query_embeddings, list) or len(query_embeddings) == 0 or not isinstance(query_embeddings[0], list):
                    logger.warning(f"Embedding format invalide: {type(query_embeddings)}")
                    # Fallback sur query_texts
                    query_params = {
                        "query_texts": [query],
                        "n_results": query_n_results
                    }
                else:
                    query_params = {
                        "query_embeddings": query_embeddings,
                        "n_results": query_n_results
                    }
            else:
                query_params = {
                    "query_texts": [query],
                    "n_results": query_n_results
                }
        except Exception as e:
            logger.warning(f"Erreur lors de la préparation des embeddings: {e}")
            query_params = {
                "query_texts": [query],
                "n_results": query_n_results
            }
        
        # Ne pas utiliser de filtre where pour l'instant (trop strict)
        # On filtrera après selon la pertinence et la section
        
        # OPTIMISATION: Le cache accélère le calcul de l'embedding de la requête
        # IMPORTANT: Seul l'embedding de la question est calculé, pas les documents
        elapsed_embed = time.time() - start_embed
        start_search = time.time()
        results = collection.query(**query_params)
        elapsed_search = time.time() - start_search
        logger.debug(f"⏱️ Embedding question: {elapsed_embed:.3f}s, Recherche vectorielle: {elapsed_search:.3f}s (cache: {len(_embedding_cache)})")
        
        if not results or not results.get('documents') or not results['documents'][0]:
            logger.warning(f"Aucun résultat RAG trouvé pour: {query}")
            # Si la recherche sémantique échoue, essayer une recherche par mots-clés dans tous les documents
            logger.info("Tentative de recherche par mots-clés dans tous les documents...")
            try:
                all_data = collection.get()
                if all_data and all_data.get("ids") and len(all_data["ids"]) > 0:
                    query_lower = query.lower()
                    query_words = set(query_lower.split())
                    
                    matching_docs = []
                    matching_metas = []
                    
                    for i, doc in enumerate(all_data.get("documents", [])):
                        if doc:
                            doc_lower = doc.lower()
                            # Compter les mots de la requête présents dans le document
                            matches = sum(1 for word in query_words if word in doc_lower and len(word) > 3)
                            if matches > 0:
                                matching_docs.append(doc)
                                meta = all_data.get("metadatas", [{}])[i] if i < len(all_data.get("metadatas", [])) else {}
                                matching_metas.append(meta)
                    
                    if matching_docs:
                        logger.info(f"Recherche par mots-clés: {len(matching_docs)} documents trouvés")
                        # Prendre les premiers résultats
                        documents = matching_docs[:n_results]
                        metadatas = matching_metas[:n_results]
                        distances = [0.0] * len(documents)  # Pas de distance pour la recherche par mots-clés
                    else:
                        logger.warning("Aucun document ne correspond aux mots-clés de la requête")
                        return "", []
                else:
                    return "", []
            except Exception as e:
                logger.error(f"Erreur lors de la recherche par mots-clés: {e}")
                return "", []
        else:
            documents = results['documents'][0]
            metadatas = results.get('metadatas', [None] * len(documents))[0] if results.get('metadatas') else [None] * len(documents)
            distances = results.get('distances', [None] * len(documents))[0] if results.get('distances') else [None] * len(documents)
        
            # Formater le contexte avec métadonnées pour plus de clarté
            formatted_contexts = []
            sources = []
            seen_sources = set()  # Pour éviter les doublons
            
            # Normaliser la section de filtre si elle existe
            filter_section_normalized = None
            if filter_section:
                filter_section_normalized = filter_section.lower().replace(" ", "-").replace("_", "-")
            
            # OPTIMISATION REPOCHAT: Post-filtrage intelligent par mots-clés
            # Scorer les documents par pertinence (distance + mots-clés)
            scored_docs = []
            for i, doc in enumerate(documents):
                if not doc or not doc.strip():
                    continue
                
                meta = metadatas[i] if i < len(metadatas) else {}
                distance = distances[i] if i < len(distances) else None
                
                # Score de pertinence combiné (distance + mots-clés)
                doc_lower = doc.lower()
                keyword_matches = sum(1 for word in query_words if word in doc_lower)
                keyword_score = keyword_matches * 0.1  # Bonus pour mots-clés
                
                # Normaliser la distance (plus petite = meilleure)
                distance_score = (1.0 / (distance + 0.1)) if distance is not None else 0.5
                
                # Score combiné
                combined_score = distance_score + keyword_score
                scored_docs.append((combined_score, i, doc, meta, distance))
            
            # Trier par score décroissant et prendre les meilleurs
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            scored_docs = scored_docs[:n_results]  # Limiter aux n_results meilleurs
            
            # Logger les distances pour diagnostic
            logger.debug(f"RAG: {len(documents)} documents → {len(scored_docs)} après post-filtrage")
            
            for score, i, doc, meta, distance in scored_docs:
                if not doc or not doc.strip():
                    logger.debug(f"Document {i} vide, ignoré")
                    continue
                
                distance_str = f"{distance:.3f}" if distance is not None else "None"
                logger.debug(f"Document {i}: distance={distance_str}, section={meta.get('section', 'N/A')}, title={meta.get('title', 'N/A')[:50]}")
                
                # Filtrer par distance si disponible (seuil adaptatif selon le type d'embedding)
                # Pour Ollama (dimension 3072), les distances peuvent être très élevées (4000-10000+)
                # Pour sentence-transformers/HF, les distances sont généralement < 1.0
                # IMPORTANT: Être très permissif pour ne pas filtrer tous les résultats
                if distance is not None:
                    # Seuil adaptatif basé sur la moyenne des distances
                    # Si toutes les distances sont élevées (> 1000), c'est probablement Ollama
                    valid_distances = [d for d in distances if d is not None]
                    if valid_distances:
                        avg_distance = sum(valid_distances) / len(valid_distances)
                        
                        if avg_distance > 1000:
                            # Ollama: utiliser un seuil très permissif (moyenne + 100% pour être sûr)
                            max_distance = avg_distance * 2.0
                            logger.debug(f"Ollama détecté (avg={avg_distance:.3f}), seuil très permissif: {max_distance:.3f}")
                        else:
                            # sentence-transformers/HF: seuil très permissif aussi
                            max_distance = 5.0  # Augmenté de 3.0 à 5.0 pour être plus permissif
                        
                        if distance > max_distance:
                            logger.debug(f"Document {i} filtré par distance: {distance:.3f} > {max_distance:.3f}")
                            # Ne pas continuer, mais ne pas non plus bloquer - on garde quand même si c'est le seul résultat
                            if len(documents) > 5:  # Seulement filtrer si on a beaucoup de résultats
                                continue
                
                # Filtrer par section si spécifiée (très flexible - ne pas être strict du tout)
                # IMPORTANT: Ne filtrer par section que si on a beaucoup de résultats, sinon garder tout
                if filter_section_normalized and meta and len(documents) > 10:
                    meta_section = meta.get('section', '').lower().replace(" ", "-").replace("_", "-")
                    if meta_section:
                        # Vérifier si la section correspond (exacte ou contient)
                        # Si la section ne correspond pas, on garde quand même si la distance est raisonnable
                        if filter_section_normalized not in meta_section and meta_section not in filter_section_normalized:
                            # Seuil adaptatif pour la distance selon le type d'embedding
                            valid_distances = [d for d in distances if d is not None]
                            if valid_distances:
                                avg_distance = sum(valid_distances) / len(valid_distances)
                                section_distance_threshold = avg_distance * 1.5 if avg_distance > 1000 else 2.0
                                
                                if distance is None or distance > section_distance_threshold:
                                    logger.debug(f"Document {i} filtré par section: {meta_section} != {filter_section_normalized} (distance: {distance:.3f})")
                                    continue
                                else:
                                    # Distance acceptable, on garde même si la section ne correspond pas exactement
                                    logger.debug(f"Document {i} gardé malgré section différente (distance acceptable: {distance:.3f})")
                
                context_parts = []
                
                # Ajouter le titre et la section si disponibles (formatage amélioré)
                if meta:
                    if meta.get('title'):
                        context_parts.append(f"Titre: {meta.get('title')}")
                    if meta.get('section') and meta.get('section') != 'accueil':
                        context_parts.append(f"Section: {meta.get('section')}")
                    # Ajouter l'URL directement dans le contexte pour référence
                    if meta.get('url'):
                        context_parts.append(f"URL source: {meta.get('url')}")
                
                # Ajouter le contenu du document
                context_parts.append(f"Contenu:\n{doc}")
                
                formatted_contexts.append("\n".join(context_parts))
                
                # Extraire les sources uniques
                if meta:
                    source_key = (meta.get('url'), meta.get('title'))
                    if source_key not in seen_sources and meta.get('url'):
                        seen_sources.add(source_key)
                        sources.append({
                            'title': meta.get('title', 'Page sans titre'),
                            'section': meta.get('section', ''),
                            'url': meta.get('url', '')
                        })
            
            if not formatted_contexts:
                logger.warning(f"Tous les résultats RAG filtrés pour: {query} (documents reçus: {len(documents)})")
                return "", []
            
            # Joindre avec des séparateurs clairs
            full_context = "\n\n---\n\n".join(formatted_contexts)
            
            logger.debug(f"RAG: {len(formatted_contexts)} chunks, {len(sources)} sources")
            return full_context, sources
        
    except Exception as e:
        logger.error(f"RAG Error: {e}", exc_info=True)
        # En cas d'erreur, retourner vide mais ne pas bloquer le chat
        return "", []
