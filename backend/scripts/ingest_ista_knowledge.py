#!/usr/bin/env python3
"""
Ingest ISTA NTIC SM knowledge base into ChromaDB for RAG chatbot.
This script processes the ista_knowledge.json file and indexes it into chunks
for efficient retrieval by the AI assistant.
"""
import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import ChromaDB and embedding function from existing RAG module
import chromadb
from app.rag.ingest import _get_hf_embedding_function, _get_ollama_embedding_function, _get_sentence_transformer


def flatten_schedule(emplois_du_temps: dict) -> list[dict]:
    """Convert nested schedule structure into flat document chunks."""
    chunks = []
    
    for filiere, groups in emplois_du_temps.items():
        for group_name, schedule in groups.items():
            for day, sessions in schedule.items():
                for session in sessions:
                    chunk = {
                        "type": "emploi_du_temps",
                        "filiere": filiere,
                        "groupe": group_name,
                        "jour": day,
                        "heure": session["heure"],
                        "module": session["module"],
                        "professeur": session["professeur"],
                        "salle": session["salle"],
                        "text": f"Emploi du temps {group_name} - {day} {session['heure']}: {session['module']} avec {session['professeur']} en salle {session['salle']}"
                    }
                    chunks.append(chunk)
    
    return chunks


def flatten_efm(efm_data: dict) -> list[dict]:
    """Convert EFM schedule into flat document chunks."""
    chunks = []
    
    for year, year_data in efm_data.items():
        if year == "region":
            continue
            
        for filiere, modules in year_data.get("filières", {}).items():
            for module_info in modules:
                chunk = {
                    "type": "efm",
                    "annee": year,
                    "filiere": filiere,
                    "module": module_info["module"],
                    "date": module_info["date"],
                    "heure": module_info["time"],
                    "region": efm_data.get("region", ""),
                    "text": f"EFM {year} {filiere} - Module: {module_info['module']}, Date: {module_info['date']}, Heure: {module_info['time']}"
                }
                chunks.append(chunk)
    
    return chunks


def flatten_employment_prospects(prospects: dict) -> list[dict]:
    """Convert employment prospects into document chunks."""
    chunks = []
    
    for filiere, info in prospects.get("filières", {}).items():
        jobs = ", ".join(info.get("jobs", []))
        groups = ", ".join(info.get("groups", []))
        
        chunk = {
            "type": "debouches",
            "filiere": filiere,
            "jobs": jobs,
            "groups": groups,
            "text": f"Débouchés professionnels {filiere}: {jobs}. Groupes concernés: {groups}"
        }
        chunks.append(chunk)
    
    return chunks


def flatten_parrains(parrains_data: dict) -> list[dict]:
    """Convert class sponsors (parrains) into document chunks."""
    chunks = []
    
    for year, year_data in parrains_data.items():
        for filiere, groups in year_data.get("filières", {}).items():
            for group_name, parrain in groups.items():
                chunk = {
                    "type": "parrain",
                    "annee": year,
                    "filiere": filiere,
                    "groupe": group_name,
                    "parrain": parrain,
                    "text": f"Parrain {group_name} ({year}): {parrain}"
                }
                chunks.append(chunk)
    
    return chunks


def flatten_institution_info(institution: dict) -> list[dict]:
    """Convert institution information into document chunks."""
    chunks = []
    
    # Basic info
    chunk = {
        "type": "institution",
        "info_type": "general",
        "name": institution.get("name", ""),
        "website": institution.get("website", ""),
        "email": institution.get("email", ""),
        "text": f"ISTA NTIC SM Casablanca - Site: {institution.get('website', '')}, Email: {institution.get('email', '')}"
    }
    chunks.append(chunk)
    
    # Rules
    if "rules" in institution:
        for rule_key, rule_value in institution["rules"].items():
            chunk = {
                "type": "institution",
                "info_type": "reglement",
                "rule": rule_key,
                "text": f"Règlement: {rule_value}"
            }
            chunks.append(chunk)
    
    # Hours
    if "hours" in institution:
        for period, times in institution["hours"].items():
            chunk = {
                "type": "institution",
                "info_type": "horaires",
                "period": period,
                "entry": times.get("entry", ""),
                "portal_closure": times.get("portal_closure", ""),
                "text": f"Horaires {period}: Entrée {times.get('entry', '')}, Portail fermé à {times.get('portal_closure', '')}"
            }
            chunks.append(chunk)
    
    return chunks


def main():
    # Load ISTA knowledge
    knowledge_path = Path(__file__).parent.parent / "app" / "data" / "ista_knowledge.json"
    
    if not knowledge_path.exists():
        print(f"❌ Knowledge file not found: {knowledge_path}")
        sys.exit(1)
    
    with open(knowledge_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print("📚 Processing ISTA knowledge base...")
    
    # Flatten all data structures
    all_chunks = []
    
    # Institution info
    if "institution" in data:
        all_chunks.extend(flatten_institution_info(data["institution"]))
    
    # Employment prospects
    if "employment_prospects" in data:
        all_chunks.extend(flatten_employment_prospects(data["employment_prospects"]))
    
    # Schedules
    if "emplois_du_temps" in data:
        all_chunks.extend(flatten_schedule(data["emplois_du_temps"]))
    
    # EFM regional
    if "efm_regional" in data:
        all_chunks.extend(flatten_efm(data["efm_regional"]))
    
    # Parrains
    if "parrains" in data:
        all_chunks.extend(flatten_parrains(data["parrains"]))
    
    # Internship info
    if "internship_stage" in data:
        for year, info in data["internship_stage"].items():
            chunk = {
                "type": "stage",
                "annee": year,
                "period": info.get("period", ""),
                "duration": info.get("duration", ""),
                "groups": ", ".join(info.get("groups", [])),
                "text": f"Stage {year}: {info.get('period', '')}, Durée: {info.get('duration', '')}, Groupes: {', '.join(info.get('groups', []))}"
            }
            all_chunks.append(chunk)
    
    # Teacher absences
    if "teacher_absences" in data:
        for absence in data["teacher_absences"]:
            chunk = {
                "type": "absence_formateur",
                "name": absence.get("name", ""),
                "period": absence.get("period", ""),
                "return_date": absence.get("return_date", ""),
                "text": f"Absence {absence.get('name', '')}: {absence.get('period', '')}, Retour: {absence.get('return_date', '')}"
            }
            all_chunks.append(chunk)
    
    print(f"✅ Processed {len(all_chunks)} knowledge chunks")
    
    # Prepare documents for RAG
    documents = []
    metadatas = []
    ids = []
    
    for idx, chunk in enumerate(all_chunks):
        text = chunk.pop("text")
        documents.append(text)
        metadatas.append(chunk)
        ids.append(f"ista_knowledge_{idx}")
    
    # Add to ChromaDB
    print("🔄 Indexing into ChromaDB...")
    try:
        # Get ChromaDB path
        if os.path.exists("/app"):
            chroma_db_path = "/app/chroma_db"
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            chroma_db_path = os.path.join(root_dir, "chroma_db")
        os.makedirs(chroma_db_path, exist_ok=True)
        
        # Create ChromaDB client
        client = chromadb.PersistentClient(path=chroma_db_path)
        
        # DELETE EXISTING COLLECTION to avoid dimension mismatch
        try:
            client.delete_collection(name="ista_documents")
            print("🗑️  Deleted existing ista_documents collection to avoid dimension mismatch")
        except:
            pass
        
        # Use ChromaDB's default embedding function (same as website_content)
        print("✅ Using ChromaDB default embedding function (dimension 384)")
        embedding_function = chromadb.utils.embedding_functions.DefaultEmbeddingFunction()
        
        # Get or create collection
        collection = client.get_or_create_collection(
            name="ista_documents",
            embedding_function=embedding_function
        )
        
        # Add documents in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            collection.add(
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids
            )
            print(f"  Added batch {i//batch_size + 1}/{(len(documents) + batch_size - 1)//batch_size}")
        
        print(f"✅ Successfully indexed {len(documents)} ISTA knowledge documents!")
        print("\n📊 Summary:")
        print(f"   - Emplois du temps: {sum(1 for c in all_chunks if c.get('type') == 'emploi_du_temps')} sessions")
        print(f"   - EFM: {sum(1 for c in all_chunks if c.get('type') == 'efm')} examens")
        print(f"   - Débouchés: {sum(1 for c in all_chunks if c.get('type') == 'debouches')} filières")
        print(f"   - Parrains: {sum(1 for c in all_chunks if c.get('type') == 'parrain')} classes")
        print(f"   - Informations: {sum(1 for c in all_chunks if c.get('type') == 'institution')} items")
        print(f"   - Stages: {sum(1 for c in all_chunks if c.get('type') == 'stage')} info")
        print(f"   - Absences: {sum(1 for c in all_chunks if c.get('type') == 'absence_formateur')} absences")
        
    except Exception as e:
        print(f"❌ Error indexing documents: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
