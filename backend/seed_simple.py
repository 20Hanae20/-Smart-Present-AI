"""Seed data sourced from https://sites.google.com/view/ista-ntic-sm/"""
from pathlib import Path

import chromadb
from datetime import date

docs = [
    # Real site (updated years) ------------------------------------------------
    {
        "title": "Admission FQ DIA_CFCP_FQ 2025",
        "content": "Résultats d'admission FQ DIA_CFCP_FQ (novembre 2025). Consultez la liste officielle sur le site ISTA NTIC SM.",
        "url": "https://sites.google.com/view/ista-ntic-sm/",
    },
    {
        "title": "Rentrée 2025-2026",
        "content": "Rentrée : 3ème/2ème année le 04/09/2025, 1ère année le 06/09/2025. Emplois du temps disponibles en ligne (mise à jour régulière).",
        "url": "https://sites.google.com/view/ista-ntic-sm/emplois-du-temps",
        "keywords": ["rentrée", "démarrage", "début", "start", "reprise", "2025-2026", "date"],
    },
    {
        "title": "Stage 3ème année 2025",
        "content": "Stage en entreprise (3ème année) : début décembre 2025. Vérifiez l'emploi du temps chaque semaine; convocation fournie pour l'entreprise.",
        "url": "https://sites.google.com/view/ista-ntic-sm/",
        "keywords": ["stage", "décembre", "entreprise", "convocation"],
    },
    {
        "title": "Calendrier EFMs 2025",
        "content": "Planning des EFMs régionaux (ex. dès le 16/12 à 08h30) sur la page 'Calendrier des EFM'.",
        "url": "https://sites.google.com/view/ista-ntic-sm/calendrier-des-efm",
        "keywords": ["efm", "calendrier", "convocation", "examen", "régional"],
    },
    {
        "title": "Attestations réussite 2025",
        "content": "Attestations de réussite promotion 2025 : disponibles fin février 2025 (guichet scolarité).",
        "url": "https://sites.google.com/view/ista-ntic-sm/",
    },
    {
        "title": "Horaires portails vendredi PM",
        "content": "Vendredi après-midi : entrée 14h15, fermeture 14h30. Respecter les consignes d'accès campus.",
        "url": "https://sites.google.com/view/ista-ntic-sm/",
        "keywords": ["horaires", "portails", "vendredi", "accès"],
    },
    {
        "title": "Blouse et badge",
        "content": "Blouse + badge obligatoires pour circuler sur site et ateliers (contrôle d'accès).",
        "url": "https://sites.google.com/view/ista-ntic-sm/",
        "keywords": ["blouse", "badge", "obligatoire", "accès"],
    },
    {
        "title": "Compétition Coranique 1447",
        "content": "Compétition Coranique Ramadan 1447 : finale annoncée, lauréats célébrés à l'amphi ISTA NTIC SM.",
        "url": "https://sites.google.com/view/ista-ntic-sm/",
    },
    {
        "title": "Hackathon régional 2025",
        "content": "Hackathon régional 2025 : équipe DEVOWFS primée (innovation full-stack).",
        "url": "https://sites.google.com/view/ista-ntic-sm/",
    },
    {
        "title": "Forum entrepreneuriat 2025",
        "content": "Forum NABDA 2025 : prix Coup de Cœur pour Kenza Roussafi (GE).",
        "url": "https://sites.google.com/view/ista-ntic-sm/",
    },
    {
        "title": "Événements mensuels 2025",
        "content": "Affiches/annonces officielles (février, mars 2025...) publiées sur le site ISTA NTIC SM.",
        "url": "https://sites.google.com/view/ista-ntic-sm/",
    },
    {
        "title": "Ouverture et pauses",
        "content": "Horaires portails et pauses affichés sur le site; vérifier les créneaux avant déplacement.",
        "url": "https://sites.google.com/view/ista-ntic-sm/",
    },
    {
        "title": "Contacts et Instagram",
        "content": "Contact : istanticsm@gmail.com. Instagram : https://www.instagram.com/ntic2sm/. Actualités et célébrations.",
        "url": "https://sites.google.com/view/ista-ntic-sm/",
    },
    {
        "title": "Emplois du temps",
        "content": "Emplois du temps officiels (tous groupes) disponibles en ligne; mis à jour fréquemment.",
        "url": "https://sites.google.com/view/ista-ntic-sm/emplois-du-temps",
        "keywords": ["emploi du temps", "edt", "planning", "horaires"],
    },
    {
        "title": "Convocation EFM",
        "content": "Convocations EFMs régionaux à présenter à l'entreprise de stage; voir page calendrier EFM.",
        "url": "https://sites.google.com/view/ista-ntic-sm/calendrier-des-efm",
        "keywords": ["convocation", "efm", "examen", "régional"],
    },
    {
        "title": "Assiduité",
        "content": "Suivre l'emploi du temps hebdomadaire et les séances ajoutées (cours/révision) pour rester assidu.",
        "url": "https://sites.google.com/view/ista-ntic-sm/",
    },
    {
        "title": "Stages 2025 rappel",
        "content": "Stages 2025 : consulter emploi du temps + EFMs; convocation envoyée pour l'entreprise de stage.",
        "url": "https://sites.google.com/view/ista-ntic-sm/",
    },
    {
        "title": "Accès campus",
        "content": "Rappel accès : blouse + badge obligatoires; vendredi PM 14h15-14h30.",
        "url": "https://sites.google.com/view/ista-ntic-sm/",
    },
    {
        "title": "Félicitations lauréats",
        "content": "Lauréats distingués (hackathon, coranique) mis à l'honneur sur le site ISTA NTIC SM.",
        "url": "https://sites.google.com/view/ista-ntic-sm/",
    },

    # SmartPresence app-oriented (synthetic but logical) -----------------------
    {
        "title": "SmartPresence - Tableau de bord",
        "content": "Tableau de bord temps réel : taux de présence, retards, absences, alertes intelligentes, exports PDF/Excel.",
        "url": "smartpresence://dashboard",
    },
    {
        "title": "SmartPresence - Pointage",
        "content": "Pointage hybride : mot de passe ou reconnaissance faciale (3 photos à l'enrôlement), temps de validation < 2s.",
        "url": "smartpresence://presence",
    },
    {
        "title": "SmartPresence - Notifications",
        "content": "Notifications smart : changement de salle, convocation EFM, alerte absence, rappel stage, push web/mobile.",
        "url": "smartpresence://notifications",
        "keywords": ["notifications", "push", "alerte", "convocation", "efm"],
    },
    {
        "title": "SmartPresence - Rôles",
        "content": "Rôles : Admin (rapports, exports), Formateur (monitoring live, validations), Étudiant (justif. absences, planning).",
        "url": "smartpresence://roles",
    },
    {
        "title": "SmartPresence - Justifications",
        "content": "Justifications d'absence en ligne : dépôt de pièces, statut en temps réel, validation par scolarité/formateur.",
        "url": "smartpresence://justifications",
    },
    {
        "title": "SmartPresence - Intégrations",
        "content": "Intégrations : export vers PDF/Excel, connecteurs LMS/HR (ex. Canvas/Workday), API REST sécurisée.",
        "url": "smartpresence://integrations",
    },
    {
        "title": "SmartPresence - IA assistant",
        "content": "Assistant IA : réponses rapides sur EFM, stages, horaires, règles de présence, notifications en langage naturel.",
        "url": "smartpresence://assistant",
    },
    {
        "title": "SmartPresence - Rapports",
        "content": "Rapports prêts à l'emploi : présence hebdo/mensuelle, retards récurrents, anomalies, export CSV/PDF.",
        "url": "smartpresence://reports",
    },
    {
        "title": "SmartPresence - Sécurité",
        "content": "Sécurité : JWT, rôles, audit log, stockage chiffré, conformité RGPD-like pour données biométriques (visage).",
        "url": "smartpresence://security",
    },
    {
        "title": "SmartPresence - Mobile",
        "content": "Accès mobile : notifications push, pointage visage via caméra mobile, consultation planning et justificatifs.",
        "url": "smartpresence://mobile",
    },
    {
        "title": "SmartPresence - Live monitoring",
        "content": "Monitoring en direct des salles : présence/retard, anomalies, seuils d'alerte configurables par formateur/admin.",
        "url": "smartpresence://live",
        "keywords": ["live", "monitoring", "temps réel", "présence"],
    },
]

CHROMA_PATH = Path(__file__).resolve().parent / "chroma_db"
client = chromadb.PersistentClient(path=str(CHROMA_PATH))

# Delete old
try:
    client.delete_collection(name="website_content")
except:
    pass

# Create with NO custom embedding function (use default)
collection = client.create_collection(
    name="website_content",
    metadata={"hnsw:space": "cosine"}
)

# Add documents with richer metadata
documents = [d["content"] for d in docs]
metadatas = []
ids = []
for i, d in enumerate(docs):
    meta = {
        "title": d["title"],
        "url": d.get("url", ""),
        "source": f"seed_{i}",
        "source_type": "site" if str(d.get("url", "")).startswith("http") else "app",
    }
    if d.get("keywords"):
        # Chroma n'accepte pas les listes en metadata → chaîne CSV
        meta["keywords"] = ",".join(d["keywords"]) if isinstance(d["keywords"], list) else str(d["keywords"]) 
    metadatas.append(meta)
    ids.append(f"seed_{i}")

collection.add(documents=documents, metadatas=metadatas, ids=ids)

print(f"✅ Seeded {collection.count()} documents")

# Test query
results = collection.query(query_texts=["débouchés"], n_results=2)
print(f"✅ Test query: {len(results['ids'][0])} results")
print(f"   {results['documents'][0][0][:100]}...")
