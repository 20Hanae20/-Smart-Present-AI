
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

os.environ.setdefault("CHROMADB_DISABLE_TELEMETRY", "1")
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
        # Utiliser un chemin persistant sous le dossier backend (même que le seed)
        from pathlib import Path
        backend_dir = Path(__file__).resolve().parents[2]  # backend/app/rag -> parents[2] = backend
        chroma_db_path = str(backend_dir / "chroma_db")
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
        try:
            from chromadb.config import Settings  # pyright: ignore[reportMissingImports]
            client = chromadb.PersistentClient(path=get_chromadb_path(), settings=Settings(anonymized_telemetry=False))
        except Exception:
            client = chromadb.PersistentClient(path=get_chromadb_path())
        
        # MULTI-COLLECTION SEARCH: Query both website_content and ista_documents
        collections_to_search = []
        
        # Try to get website_content collection
        try:
            website_collection = client.get_collection(name="website_content")
            collection_data = website_collection.get()
            if collection_data.get("ids") and len(collection_data["ids"]) > 0:
                collections_to_search.append(("website_content", website_collection))
                logger.debug(f"Collection 'website_content' chargée avec {len(collection_data['ids'])} documents")
            else:
                logger.warning("Collection 'website_content' est vide")
        except Exception as e:
            logger.warning(f"Collection 'website_content' non disponible: {e}")
        
        # Try to get ista_documents collection
        try:
            ista_collection = client.get_collection(name="ista_documents")
            collection_data = ista_collection.get()
            if collection_data.get("ids") and len(collection_data["ids"]) > 0:
                collections_to_search.append(("ista_documents", ista_collection))
                logger.debug(f"Collection 'ista_documents' chargée avec {len(collection_data['ids'])} documents")
            else:
                logger.warning("Collection 'ista_documents' est vide")
        except Exception as e:
            logger.debug(f"Collection 'ista_documents' non disponible: {e}")
        
        # If no collections available, return empty
        if not collections_to_search:
            logger.warning("Aucune collection disponible. Exécutez d'abord les scripts d'ingestion")
            return "", []
        
        logger.info(f"Recherche dans {len(collections_to_search)} collection(s): {[name for name, _ in collections_to_search]}")
        
        # Construire les filtres si une section est spécifiée (mais ne pas être trop strict)
        where_clause = None
        if filter_section:
            # Normaliser la section pour la recherche (enlever espaces, convertir en minuscules)
            filter_section_normalized = filter_section.lower().replace(" ", "-").replace("_", "-")
            # Ne pas filtrer par section si elle est trop générique, mais plutôt chercher dans les résultats
            # On va faire une requête sans filtre et filtrer après selon la pertinence
            logger.info(f"Section détectée: {filter_section}, recherche sans filtre strict pour plus de résultats")
        
        # OPTIMISATION REPOCHAT: Pré-filtrage + expansion requête (synonymes fréquent)
        query_lower = query.lower()
        # Groupes d'intention simples
        intents = {
            "rentree": ["rentrée", "rentree", "démarrage", "demarrage", "début", "debut", "start", "reprise", "back", "school", "2025-2026"],
            "efm": ["efm", "examen", "regional", "régional", "convocation", "calendrier"],
            "stage": ["stage", "internship", "entreprise", "convention", "decembre", "décembre"],
            "edt": ["emploi", "edt", "planning", "horaire", "schedule", "temps"],
            "regles": ["blouse", "badge", "accès", "acces", "obligatoire"],
            "notif": ["notification", "push", "alerte", "convocation", "efm"],
            "live": ["live", "monitoring", "temps", "réel", "reel"],
            "debouches": ["debouches", "débouchés", "emploi", "métier", "travail", "carriere", "carrière", "opportunite", "opportunité"],
            "parrain": ["parrain", "mentor", "responsable", "encadrant", "coach"],
            "contact": ["contact", "email", "site", "web", "telephone", "téléphone", "adresse", "coordonnee", "coordonnées"],
            "horaires": ["horaire", "heure", "entree", "ouverture", "fermeture", "portail", "acces"],
        }

        # Extract NTIC2 group names (e.g., "NTIC2-FS201", "fs201", "dev101")
        import re
        detected_group = None
        detected_day = None
        # Match patterns like "NTIC2-FS201", "fs201", "FS201"
        group_pattern = r'(?:ntic2[- ]?)?(fs|dev|id|ge)(\d{3})'
        group_match = re.search(group_pattern, query_lower)
        if group_match:
            filiere_code = group_match.group(1).upper()
            number = group_match.group(2)
            detected_group = f"NTIC2-{filiere_code}{number}"
            logger.info(f"Groupe détecté: {detected_group}")
        
        # Extract day of week (lundi, mardi, mercredi, jeudi, vendredi)
        days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        for day in days:
            if day in query_lower:
                detected_day = day
                logger.info(f"Jour détecté: {detected_day}")
                break

        # Détecter l'intention et construire des termes d'expansion
        expanded_terms = []
        dominant_source = None  # "site" ou "app"
        detected_intent = None
        for key, terms in intents.items():
            if any(t in query_lower for t in terms):
                expanded_terms.extend(terms)
                detected_intent = key  # Track dominant intent
                if key in ("notif", "live"):
                    dominant_source = "app"
                elif key in ("rentree", "efm", "stage", "edt", "regles", "debouches", "parrain", "contact", "horaires"):
                    dominant_source = "site"

        # Construire la requête étendue (add group name for better matching)
        expanded_query = query
        if detected_group:
            expanded_query = f"{query} {detected_group} groupe emploi temps"
        elif expanded_terms:
            expanded_query = f"{query} " + " ".join(sorted(set(expanded_terms)))

        # Mots clés pour reranking (inclut expansions)
        token_words = [w for w in expanded_query.replace("/", " ").split() if len(w) > 2]
        query_words = set(token_words)
        
        # OPTIMISATION ULTRA-RAPIDE: topK=3 maximum (max 4) pour temps de réponse ≤ 1-2s
        # Le cache des embeddings accélère les requêtes répétées
        # IMPORTANT: Embeddings des documents calculés UNE SEULE FOIS lors de l'ingestion
        start_embed = time.time()
        
        # Augmenter n_results pour ISTA documents (need more candidates for metadata boost)
        query_n_results = min(n_results * 4, 20)  # Take more results to increase chance of ISTA matches
        
        # SIMPLIFIED: Use query_texts directly - ChromaDB will use its default embedding function
        query_params = {
            "query_texts": [expanded_query],
            "n_results": query_n_results
        }
        
        # MULTI-COLLECTION QUERY: Search all available collections and merge results
        all_documents = []
        all_metadatas = []
        all_distances = []
        
        elapsed_embed = time.time() - start_embed
        
        for collection_name, collection in collections_to_search:
            try:
                start_search = time.time()
                results = collection.query(**query_params)
                elapsed_search = time.time() - start_search
                logger.debug(f"⏱️ Collection '{collection_name}': Embedding {elapsed_embed:.3f}s, Recherche {elapsed_search:.3f}s")
                
                if results and results.get('documents') and results['documents'][0]:
                    docs = results['documents'][0]
                    metas = results.get('metadatas', [None] * len(docs))[0] if results.get('metadatas') else [None] * len(docs)
                    dists = results.get('distances', [None] * len(docs))[0] if results.get('distances') else [None] * len(docs)
                    
                    # Add collection source to metadata
                    for meta in metas:
                        if meta is not None:
                            meta['_collection'] = collection_name
                    
                    all_documents.extend(docs)
                    all_metadatas.extend(metas)
                    all_distances.extend(dists)
                    
                    logger.info(f"Collection '{collection_name}': {len(docs)} résultats trouvés")
            except Exception as e:
                logger.error(f"Erreur lors de la recherche dans '{collection_name}': {e}")
        
        # If no results from any collection, try keyword search fallback
        if not all_documents:
            logger.warning(f"Aucun résultat RAG trouvé pour: {query}")
            logger.info("Tentative de recherche par mots-clés dans toutes les collections...")
            
            for collection_name, collection in collections_to_search:
                try:
                    all_data = collection.get()
                    if all_data and all_data.get("ids") and len(all_data["ids"]) > 0:
                        query_lower = query.lower()
                        query_words_kw = set(query_lower.split())
                        
                        for i, doc in enumerate(all_data.get("documents", [])):
                            if doc:
                                doc_lower = doc.lower()
                                matches = sum(1 for word in query_words_kw if word in doc_lower and len(word) > 3)
                                if matches > 0:
                                    all_documents.append(doc)
                                    meta = all_data.get("metadatas", [{}])[i] if i < len(all_data.get("metadatas", [])) else {}
                                    if meta:
                                        meta['_collection'] = collection_name
                                    all_metadatas.append(meta)
                                    all_distances.append(0.0)
                        
                        if all_documents:
                            logger.info(f"Recherche par mots-clés dans '{collection_name}': {len(all_documents)} documents")
                except Exception as e:
                    logger.error(f"Erreur recherche mots-clés dans '{collection_name}': {e}")
            
            if not all_documents:
                logger.warning("Aucun document ne correspond aux mots-clés de la requête")
                return "", []
        
        # DON'T sort by distance yet - we need to apply ISTA boost first
        # Just combine all results
        combined_results = list(zip(all_documents, all_metadatas, all_distances))
        
        print(f"[DEBUG] Combined {len(combined_results)} total results from {len(collections_to_search)} collections")
        
        # DON'T limit yet - score all documents first with ISTA boost
        documents = [r[0] for r in combined_results]
        metadatas = [r[1] for r in combined_results]
        distances = [r[2] for r in combined_results]
        
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
            title_lower = (meta.get('title') or '').lower()
            meta_keywords = meta.get('keywords') or []
            if isinstance(meta_keywords, str):
                # au cas où ce soit une chaîne séparée par des virgules
                meta_keywords = [k.strip() for k in meta_keywords.split(',') if k.strip()]
            meta_kw_lower = [k.lower() for k in meta_keywords]

            # Compter les occurrences dans doc + titre + keywords
            keyword_matches = sum(1 for word in query_words if (word in doc_lower) or (word in title_lower) or (word in meta_kw_lower))
            keyword_score = keyword_matches * 0.2  # Bonus plus fort pour être plus directionnel
            
            # BOOST FOR ISTA DOCUMENTS: Strong bonus for exact metadata matches
            ista_boost = 0.0
            if meta.get('_collection') == 'ista_documents':
                groupe = meta.get('groupe', '')
                jour = meta.get('jour', '')
                doc_type = meta.get('type', '')
                
                # STRONG BOOST basé sur l'intention détectée - VERY AGGRESSIVE
                if detected_intent == 'edt' and doc_type == 'emploi_du_temps':
                    ista_boost += 10.0  # MAXIMUM boost for schedule queries
                elif detected_intent == 'efm' and doc_type == 'efm':
                    ista_boost += 10.0  # MAXIMUM boost for EFM queries
                elif detected_intent == 'debouches' and doc_type == 'debouches':
                    ista_boost += 10.0  # MAXIMUM boost for employment queries
                elif detected_intent == 'parrain' and doc_type == 'parrain':
                    ista_boost += 10.0  # MAXIMUM boost for sponsor queries
                elif detected_intent == 'contact' and doc_type == 'institution':
                    ista_boost += 10.0  # MAXIMUM boost for contact queries
                elif detected_intent == 'stage' and doc_type == 'stage':
                    ista_boost += 10.0  # MAXIMUM boost for internship queries
                elif detected_intent == 'regles' and doc_type == 'institution':
                    ista_boost += 10.0  # MAXIMUM boost for rules queries
                elif detected_intent == 'horaires' and meta.get('info_type') == 'horaires':
                    ista_boost += 10.0  # MAXIMUM boost for hours queries
                else:
                    # Penalty for WRONG type when intent is detected
                    if detected_intent and detected_intent != 'edt':
                        if doc_type == 'emploi_du_temps':
                            ista_boost -= 5.0  # Penalize schedule docs when other type expected
                
                # Check for exact group match using detected_group
                if detected_group and groupe and groupe.upper() == detected_group.upper():
                    ista_boost += 5.0  # VERY strong boost for exact detected group
                elif groupe and groupe.lower() in query_lower:
                    ista_boost += 3.0  # Strong boost for group mention
                
                # Check for day match using detected_day
                if detected_day and jour and jour.lower() == detected_day.lower():
                    ista_boost += 3.0  # Strong boost for exact day match
                elif jour and jour.lower() in query_lower:
                    ista_boost += 1.5  # Medium boost for day mention
                
                # Check for module/professor match
                if meta.get('module') and any(word in meta.get('module', '').lower() for word in query_words):
                    ista_boost += 0.8
                if meta.get('professeur') and any(word in meta.get('professeur', '').lower() for word in query_words):
                    ista_boost += 0.8
                
                # General ISTA relevance boost
                ista_boost += 0.5
            
            # Normaliser la distance (plus petite = meilleure)
            distance_score = (1.0 / (distance + 0.1)) if distance is not None else 0.5
            
            # Léger boost selon la source dominante
            boost = 0.0
            source_type = meta.get('source_type')
            if dominant_source and source_type:
                if dominant_source == source_type:
                    boost += 0.2
            
            # Score combiné (include ista_boost)
            combined_score = distance_score + keyword_score + boost + ista_boost
            scored_docs.append((combined_score, i, doc, meta, distance))
        
        # Trier par score décroissant et prendre les meilleurs
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        max_docs = 1  # Réponse courte, un seul extrait
        scored_docs = scored_docs[:max_docs]
        
        # Logger les distances pour diagnostic
        logger.debug(f"RAG: {len(documents)} documents → {len(scored_docs)} après post-filtrage")
        
        for score, i, doc, meta, distance in scored_docs:
            if not doc or not doc.strip():
                logger.debug(f"Document {i} vide, ignoré")
                continue
            
            distance_str = f"{distance:.3f}" if distance is not None else "None"
            collection_name = meta.get('_collection', 'unknown') if meta else 'unknown'
            logger.debug(f"Document {i} [{collection_name}]: distance={distance_str}, section={meta.get('section', 'N/A')}, title={meta.get('title', 'N/A')[:50]}")
            
            # Filtrer par distance si disponible (seuil adaptatif selon le type d'embedding)
            # Pour Ollama (dimension 3072), les distances peuvent être très élevées (4000-10000+)
            # Pour sentence-transformers/HF, les distances sont généralement < 1.0
            # IMPORTANT: Être très permissif pour ne pas filtrer tous les résultats
            # Distance filtering disabled to keep sparse results
            
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
            
            # Format differently for ISTA documents vs website content
            if meta and meta.get('_collection') == 'ista_documents':
                # ISTA document - use structured metadata
                if meta.get('type') == 'emploi_du_temps':
                    # Schedule entry
                    groupe = meta.get('groupe', 'Groupe inconnu')
                    jour = meta.get('jour', '').capitalize()
                    heure = meta.get('heure', '')
                    module = meta.get('module', '')
                    professeur = meta.get('professeur', '')
                    salle = meta.get('salle', '')
                    
                    context_parts.append(f"📅 Emploi du temps - {groupe}")
                    context_parts.append(f"🕐 {jour} {heure}")
                    context_parts.append(f"📚 Module: {module}")
                    context_parts.append(f"👨‍🏫 Professeur: {professeur}")
                    context_parts.append(f"🏫 Salle: {salle}")
                    
                elif meta.get('type') == 'efm':
                    # Exam entry
                    module = meta.get('module', '')
                    date = meta.get('date', '')
                    heure = meta.get('heure', '')
                    
                    context_parts.append(f"📝 Examen EFM")
                    context_parts.append(f"📚 Module: {module}")
                    context_parts.append(f"📅 Date: {date}")
                    context_parts.append(f"🕐 Heure: {heure}")
                    
                elif meta.get('type') == 'parrain':
                    # Class sponsor
                    groupe = meta.get('groupe', '')
                    nom = meta.get('parrain', '')  # FIX: Use 'parrain' key, not 'nom'
                    
                    context_parts.append(f"👥 Parrain de classe")
                    context_parts.append(f"Groupe: {groupe}")
                    context_parts.append(f"Parrain: {nom}")
                    
                else:
                    # Other ISTA content - just show the text
                    context_parts.append(doc)
                    
            else:
                # Website content - original format
                if meta:
                    if meta.get('title'):
                        context_parts.append(f"Titre: {meta.get('title')}")
                    if meta.get('section') and meta.get('section') != 'accueil':
                        context_parts.append(f"Section: {meta.get('section')}")
                    if meta.get('url'):
                        context_parts.append(f"URL source: {meta.get('url')}")
                
                # Ajouter le contenu du document
                max_len = 600
                truncated = doc if len(doc) <= max_len else doc[:max_len].rstrip() + "..."
                context_parts.append(f"Contenu:\n{truncated}")
            
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
            # Fallback: prendre les premiers documents sans filtrage strict
            fallback_sources = []
            for i, doc in enumerate(documents[:n_results]):
                if not doc or not doc.strip():
                    continue
                meta = metadatas[i] if i < len(metadatas) else {}
                parts = []
                if meta.get('title'):
                    parts.append(f"Titre: {meta.get('title')}")
                if meta.get('section') and meta.get('section') != 'accueil':
                    parts.append(f"Section: {meta.get('section')}")
                if meta.get('url'):
                    parts.append(f"URL source: {meta.get('url')}")
                parts.append(f"Contenu:\n{doc}")
                formatted_contexts.append("\n".join(parts))
                if meta.get('url'):
                    fallback_sources.append({
                        'title': meta.get('title', 'Source'),
                        'section': meta.get('section', ''),
                        'url': meta.get('url', '')
                    })
            if formatted_contexts:
                full_context = "\n\n---\n\n".join(formatted_contexts)
                return full_context, fallback_sources
            return "", []
        
        # Joindre avec des séparateurs clairs
        full_context = "\n\n---\n\n".join(formatted_contexts)
        
        logger.debug(f"RAG: {len(formatted_contexts)} chunks, {len(sources)} sources")
        return full_context, sources
        
    except Exception as e:
        logger.error(f"RAG Error: {e}", exc_info=True)
        # En cas d'erreur, retourner vide mais ne pas bloquer le chat
        return "", []
