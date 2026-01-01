#!/usr/bin/env python3
"""
Script pour rafraîchir les données ISTA NTIC depuis le site officiel
https://sites.google.com/view/ista-ntic-sm/
"""

import sys
import os
from pathlib import Path

# Ajouter le chemin du backend au PYTHONPATH
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import requests
from bs4 import BeautifulSoup
import chromadb
from chromadb.utils import embedding_functions
import time
import re
from urllib.parse import urljoin, urlparse
import logging
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://sites.google.com/view/ista-ntic-sm/"

# Toutes les sections du site ISTA NTIC
PAGES_TO_SCRAPE = [
    "",  # Page d'accueil
    "emplois-du-temps",
    "documents",
    "résultats-fin-année",
    "calendrier-des-efm",
    "notes-discipline",
    "stage",
    "liste-des-parrains-de-groupe",
    "règlement-intérieur-assiduité-et-comportement",
    "annonces",
    "scholarvox",
    "activités-para-formation",
    "liens-utiles",
    "contact"
]

def get_embedding_function():
    """Crée la fonction d'embedding - utilise ChromaDB par défaut si pas d'API key"""
    # Essayer d'utiliser l'embedding function par défaut de ChromaDB
    # qui fonctionne sans API key
    try:
        # ChromaDB utilise sentence-transformers en local par défaut
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        logger.info("Utilisation de DefaultEmbeddingFunction (ChromaDB)")
        return DefaultEmbeddingFunction()
    except Exception as e:
        logger.warning(f"DefaultEmbeddingFunction non disponible: {e}")
        # Fallback: utiliser None pour laisser ChromaDB utiliser sa fonction par défaut
        logger.info("Utilisation de la fonction d'embedding par défaut de ChromaDB")
        return None

def scrape_page_content(url):
    """Scrape le contenu d'une page Google Sites avec extraction améliorée"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        
        logger.info(f"Scraping: {url}")
        response = requests.get(url, timeout=15, headers=headers, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extraire le titre
        title_elem = soup.find('title')
        title = title_elem.get_text(strip=True) if title_elem else "Page sans titre"
        
        # Nettoyer les éléments non-textuels
        for element in soup(["script", "style", "nav", "header", "footer", "iframe"]):
            element.decompose()
        
        # Collecter tout le texte visible
        text_parts = []
        
        # Google Sites utilise des divs spécifiques pour le contenu
        # Chercher tous les éléments textuels dans l'ordre
        main_content = soup.find('body')
        
        if main_content:
            # Extraire TOUT le texte visible en préservant l'ordre
            for element in main_content.descendants:
                if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    text = element.get_text(strip=True)
                    if text and text not in text_parts:
                        level = int(element.name[1])
                        text_parts.append(f"{'#' * level} {text}")
                
                elif element.name == 'p':
                    text = element.get_text(strip=True)
                    if text and len(text) > 5 and text not in text_parts:
                        text_parts.append(text)
                
                elif element.name == 'li':
                    text = element.get_text(strip=True)
                    if text and text not in text_parts:
                        text_parts.append(f"• {text}")
                
                elif element.name in ['td', 'th']:
                    # Pour les cellules de tableau
                    text = element.get_text(strip=True)
                    if text and len(text) > 2:
                        # Ne pas ajouter si c'est déjà dans un autre contexte
                        pass
                
                elif element.name == 'a':
                    # Extraire les liens avec leur texte
                    text = element.get_text(strip=True)
                    href = element.get('href', '')
                    if text and href and 'http' in href:
                        link_text = f"{text} (lien: {href})"
                        if link_text not in text_parts:
                            text_parts.append(link_text)
                
                elif element.name == 'span' or element.name == 'div':
                    # Pour les spans et divs, vérifier s'ils contiennent du texte direct
                    if element.string and element.string.strip():
                        text = element.string.strip()
                        if len(text) > 10 and text not in text_parts:
                            # Vérifier que ce n'est pas déjà capturé par un parent
                            parent_text = element.parent.get_text(strip=True) if element.parent else ""
                            if text != parent_text:
                                text_parts.append(text)
        
        # Si toujours vide, extraire tout le texte brut
        if len(text_parts) < 3:
            logger.warning(f"Peu de contenu extrait pour {url}, tentative d'extraction brute...")
            all_text = soup.get_text(separator='\n', strip=True)
            # Nettoyer et filtrer
            lines = [line.strip() for line in all_text.split('\n') if line.strip()]
            # Filtrer les lignes trop courtes ou répétitives
            filtered_lines = []
            for line in lines:
                if len(line) > 10 and line not in filtered_lines:
                    # Éviter les éléments de navigation communs
                    if not any(nav_word in line.lower() for nav_word in ['cookie', 'google sites', 'report abuse', 'page updated']):
                        filtered_lines.append(line)
            
            text_parts = filtered_lines[:50]  # Limiter à 50 lignes max
        
        # Joindre tout le contenu
        full_content = "\n\n".join(text_parts)
        
        # Nettoyer les espaces multiples
        full_content = re.sub(r'\n{3,}', '\n\n', full_content)
        full_content = re.sub(r' +', ' ', full_content)
        
        logger.info(f"Extrait {len(full_content)} caractères depuis {title}")
        
        return {
            'title': title,
            'content': full_content.strip(),
            'url': url,
            'scraped_at': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Erreur scraping {url}: {e}")
        return None

def chunk_text(text, chunk_size=800, overlap=100):
    """Découpe le texte en chunks avec chevauchement"""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk.strip())
    
    return chunks

def refresh_chromadb():
    """Rafraîchit complètement ChromaDB avec les dernières données du site ISTA"""
    logger.info("🚀 Démarrage du rafraîchissement des données ISTA NTIC")
    
    # Chemin ChromaDB
    chroma_path = backend_dir / "chroma_db"
    chroma_path.mkdir(exist_ok=True)
    
    # Initialiser ChromaDB
    logger.info(f"📂 Initialisation ChromaDB: {chroma_path}")
    client = chromadb.PersistentClient(path=str(chroma_path))
    
    # Supprimer l'ancienne collection
    try:
        client.delete_collection(name="website_content")
        logger.info("🗑️  Ancienne collection supprimée")
    except:
        pass
    
    # Créer nouvelle collection
    embedding_fn = get_embedding_function()
    
    if embedding_fn:
        collection = client.create_collection(
            name="website_content",
            embedding_function=embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
    else:
        # Utiliser la fonction d'embedding par défaut de ChromaDB
        collection = client.create_collection(
            name="website_content",
            metadata={"hnsw:space": "cosine"}
        )
    logger.info("✅ Nouvelle collection créée")
    
    # Scraper toutes les pages
    all_documents = []
    all_metadatas = []
    all_ids = []
    
    for i, page_path in enumerate(PAGES_TO_SCRAPE):
        url = urljoin(BASE_URL, page_path)
        
        # Scraper la page
        page_data = scrape_page_content(url)
        
        if page_data and page_data['content']:
            # Découper en chunks
            chunks = chunk_text(page_data['content'])
            
            logger.info(f"📄 {page_data['title']}: {len(chunks)} chunks")
            
            for j, chunk in enumerate(chunks):
                doc_id = f"doc_{i}_{j}"
                all_ids.append(doc_id)
                all_documents.append(chunk)
                all_metadatas.append({
                    'source': url,
                    'url': url,
                    'title': page_data['title'],
                    'chunk_index': j,
                    'total_chunks': len(chunks),
                    'scraped_at': page_data['scraped_at']
                })
        
        # Pause pour ne pas surcharger le serveur
        time.sleep(1)
    
    # Ajouter tous les documents à ChromaDB
    if all_documents:
        logger.info(f"💾 Ajout de {len(all_documents)} chunks à ChromaDB...")
        
        # Ajouter par batches de 100
        batch_size = 100
        for i in range(0, len(all_documents), batch_size):
            batch_end = min(i + batch_size, len(all_documents))
            collection.add(
                documents=all_documents[i:batch_end],
                metadatas=all_metadatas[i:batch_end],
                ids=all_ids[i:batch_end]
            )
            logger.info(f"  ✓ Batch {i//batch_size + 1}: {batch_end - i} documents")
            time.sleep(0.5)
        
        logger.info(f"✅ {len(all_documents)} documents ajoutés avec succès!")
    else:
        logger.warning("⚠️  Aucun document à ajouter")
    
    # Vérifier le résultat
    final_count = len(collection.get()["ids"])
    logger.info(f"📊 Total final: {final_count} chunks dans ChromaDB")
    
    # Sauvegarder un résumé
    summary = {
        'total_chunks': final_count,
        'pages_scraped': len(PAGES_TO_SCRAPE),
        'refreshed_at': datetime.now().isoformat(),
        'base_url': BASE_URL
    }
    
    summary_path = backend_dir / "chroma_db" / "refresh_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"💾 Résumé sauvegardé: {summary_path}")
    logger.info("🎉 Rafraîchissement terminé avec succès!")
    
    return final_count

if __name__ == "__main__":
    try:
        refresh_chromadb()
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        sys.exit(1)
