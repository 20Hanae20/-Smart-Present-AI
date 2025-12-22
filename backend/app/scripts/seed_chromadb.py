#!/usr/bin/env python3
"""
Seed ChromaDB with SmartPresence knowledge base - EXACT NTIC2 pattern
Run this script to initialize the vector database with initial documents.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_agent.rag_pipeline import seed_smartpresence_knowledge, init_collection, get_chromadb_path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Seed ChromaDB with knowledge base."""
    logger.info("=" * 60)
    logger.info("ChromaDB Seeding Script - EXACT NTIC2")
    logger.info("=" * 60)
    
    # Show ChromaDB path
    chroma_path = get_chromadb_path()
    logger.info(f"ChromaDB Path: {chroma_path}")
    
    # Initialize collection
    logger.info("Initializing collection...")
    collection = init_collection()
    
    if not collection:
        logger.error("❌ Failed to initialize collection")
        return False
    
    # Check current count
    try:
        current_count = collection.count()
        logger.info(f"Current document count: {current_count}")
    except Exception as e:
        logger.warning(f"Could not get count: {e}")
        current_count = 0
    
    # Seed data
    logger.info("Seeding knowledge base...")
    success = seed_smartpresence_knowledge()
    
    if success:
        try:
            new_count = collection.count()
            logger.info(f"✅ Seeding complete! Documents: {new_count}")
        except Exception:
            logger.info("✅ Seeding complete!")
    else:
        logger.error("❌ Seeding failed")
    
    logger.info("=" * 60)
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
