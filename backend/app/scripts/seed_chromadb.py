"""
Seed ChromaDB with Smart Presence knowledge base
EXACT NTIC2 pattern for database initialization
"""

import logging
import sys
import os

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ai_agent.rag_pipeline import seed_smartpresence_knowledge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main seeding function"""
    logger.info("Starting ChromaDB seeding...")
    
    try:
        seed_smartpresence_knowledge()
        logger.info("✅ ChromaDB seeding completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
