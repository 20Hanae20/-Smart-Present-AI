"""Create test ChromaDB data for the chatbot"""
import chromadb

client = chromadb.PersistentClient(path="/app/chroma_db")

# Create collection
collection = client.create_collection(
    name="website_content",
    metadata={"hnsw:space": "cosine"}
)

# Add FAQ data
docs = [
    "L'admission à l'ISTA se fait sur dossier et entretien. Vous devez avoir un bac ou équivalent.",
    "Les frais de scolarité sont de 3000 DH par mois. Des bourses sont disponibles pour les étudiants méritants.",
    "La période de stage est de 3 mois minimum. Il doit être validé par un tuteur académique et un maître de stage.",
    "Les absences doivent être justifiées auprès de la direction pédagogique dans les 48 heures.",
    "Les débouchés après l'ISTA incluent développeur web, développeur mobile, testeur QA, analyste de données, administrateur systèmes.",
    "Le contact direct pour les infos est contact@ista.ma ou appelez le 0500000000.",
    "Les professeurs parrains sont assignés au début de chaque formation pour accompagner les étudiants.",
    "Le menu principal vous permet d'accéder à toutes les fonctionnalités de la plateforme.",
    "Les examens de fin de module (EFM) sont organisés par région et ont lieu deux fois par an.",
    "La durée de formation au ISTA est de 2 ans pour le technicien et 2 ans et demi pour le technicien spécialisé.",
]

ids = [f"doc_{i}" for i in range(len(docs))]

collection.add(ids=ids, documents=docs)

print(f"✅ Created collection with {collection.count()} documents")

# Test query
results = collection.query(query_texts=["débouchés"], n_results=2)
print(f"✅ Test query returned {len(results['ids'][0])} results")
