"""Seed logical synthetic data so the assistant can answer key ISTA NTIC questions.

Run inside the ntic2_backend container:
    python -m app.rag.custom_seed
"""

from datetime import date
from typing import List, Dict

import chromadb  # pyright: ignore[reportMissingImports]

from app.rag.pipeline import get_chromadb_path, get_embedding_function


def seed_documents() -> List[Dict]:
    """Return a list of synthetic but plausible documents to cover common questions."""

    current_year = date.today().year
    efm_year = current_year if date.today().month <= 8 else current_year + 1

    return [
        {
            "title": "Calendrier des EFM régionaux",
            "url": "synthetic://efm-regional-calendar",
            "section": "calendrier efm",
            "content": (
                f"Calendrier des EFM régionaux {efm_year}\n"
                "- Épreuves écrites : 12 au 16 mars\n"
                "- Épreuves pratiques : 02 au 06 avril\n"
                "- Session de rattrapage : 14 au 16 mai\n"
                "- Publication des résultats : 28 mai\n"
                "- Dépôt des réclamations : 29 mai au 31 mai\n"
                "- Clôture administrative : 05 juin\n"
                "Les dates sont indicatives et confirmées par la direction des études."
            ),
        },
        {
            "title": "Professeur Parrain - 1ère année",
            "url": "synthetic://prof-parrain-1a",
            "section": "professeur parrain",
            "content": (
                "Professeur parrain 1ère année :\n"
                "- Nom : Mme. Fatima Zahra El Idrissi\n"
                "- Permanence : Mardi 14h-16h, Salle B203\n"
                "- Contact : fatima.elidrissi@ista-ntic.ma\n"
                "- Rôle : suivi pédagogique, stages, réorientation."
            ),
        },
        {
            "title": "Professeur Parrain - 2ème année",
            "url": "synthetic://prof-parrain-2a",
            "section": "professeur parrain",
            "content": (
                "Professeur parrain 2ème année :\n"
                "- Nom : M. Youssef Amrani\n"
                "- Permanence : Jeudi 10h-12h, Salle A105\n"
                "- Contact : youssef.amrani@ista-ntic.ma\n"
                "- Rôle : mémoire de fin d'études, insertion professionnelle."
            ),
        },
        {
            "title": "Professeur Parrain - 3ème année",
            "url": "synthetic://prof-parrain-3a",
            "section": "professeur parrain",
            "content": (
                "Professeur parrain 3ème année :\n"
                "- Nom : Mme. Salma Bennis\n"
                "- Permanence : Lundi 15h-17h, Salle C301\n"
                "- Contact : salma.bennis@ista-ntic.ma\n"
                "- Rôle : projets avancés, networking entreprises, poursuite d'études."
            ),
        },
        {
            "title": "Débouchés après formation",
            "url": "synthetic://debouches",
            "section": "debouches",
            "content": (
                "Débouchés typiques des lauréats ISTA NTIC :\n"
                "- Développeur web / mobile\n"
                "- Analyste de données junior\n"
                "- Technicien systèmes et réseaux\n"
                "- Spécialiste support applicatif\n"
                "- Consultant TI junior\n"
                "- Administrateur bases de données\n"
                "- Entrepreneur (services numériques, intégration).\n"
                "Compétences renforcées : Git, DevOps de base, cybersécurité, bonnes pratiques UX."
            ),
        },
        {
            "title": "Supports de cours",
            "url": "synthetic://supports-cours",
            "section": "support",
            "content": (
                "Supports de cours disponibles :\n"
                "- Plateforme interne : https://intra.ista-ntic.ma/supports\n"
                "- Accès par filière et année (onglet Étudiants > Supports de cours).\n"
                "- Formats : PDF, slides, enregistrements courts.\n"
                "- Problème d'accès : contacter support@ista-ntic.ma avec votre CNE."
            ),
        },
        {
            "title": "Contacts ISTA",
            "url": "synthetic://contact-ista",
            "section": "contact",
            "content": (
                "Contacts utiles ISTA NTIC Sidi Maarouf :\n"
                "- Accueil : 0522 00 00 00\n"
                "- Scolarité : scolarite@ista-ntic.ma\n"
                "- Stages / entreprises : stages@ista-ntic.ma\n"
                "- Informatique / accès plateforme : support@ista-ntic.ma\n"
                "- Adresse : Bd Moulay Thami, Sidi Maarouf, Casablanca."
            ),
        },
        {
            "title": "Stages et PFEs",
            "url": "synthetic://stages",
            "section": "stage",
            "content": (
                "Stages et PFEs :\n"
                "- Durée : 8 à 10 semaines (avril-juin).\n"
                "- Convention : à retirer à la scolarité, signée par l'entreprise.\n"
                "- Rapport : 25-30 pages, soutenance fin juin.\n"
                "- Suivi : professeur parrain + encadrant entreprise.\n"
                "- Dépôt du rapport : 10 jours avant la soutenance."
            ),
        },
        {
            "title": "Absences et discipline",
            "url": "synthetic://absences",
            "section": "notes discipline",
            "content": (
                "Absences et discipline :\n"
                "- Seuil d'absences : 20% par module => exclusion possible.\n"
                "- Justificatifs : à déposer sous 48h (médecin, cas de force majeure).\n"
                "- Avertissements : 1er rappel, 2e avertissement, conseil de discipline.\n"
                "- Retards : 3 retards = 1 absence."
            ),
        },
        {
            "title": "Documents administratifs",
            "url": "synthetic://documents",
            "section": "documents",
            "content": (
                "Documents disponibles :\n"
                "- Attestation de scolarité (délai 48h).\n"
                "- Relevé de notes (fin de semestre).\n"
                "- Certificat de stage (après validation du rapport).\n"
                "- Demande en ligne : https://intra.ista-ntic.ma/demandes."
            ),
        },
    ]


def upsert_seed():
    docs = seed_documents()
    client = chromadb.PersistentClient(path=get_chromadb_path())
    embedding_function = get_embedding_function()
    collection = client.get_or_create_collection(
        name="website_content",
        embedding_function=embedding_function,
    )

    documents = [d["content"] for d in docs]
    metadatas = [
        {
            "title": d["title"],
            "url": d["url"],
            "source": d["url"],
            "section": d["section"],
            "chunk_index": 0,
            "total_chunks": 1,
        }
        for d in docs
    ]
    ids = [f"seed_{i}" for i in range(len(docs))]

    # Remove old seeds to avoid duplicates
    try:
        existing = collection.get(ids=ids)
        if existing and existing.get("ids"):
            collection.delete(ids=ids)
    except Exception:
        pass

    collection.add(documents=documents, metadatas=metadatas, ids=ids)


if __name__ == "__main__":
    upsert_seed()
