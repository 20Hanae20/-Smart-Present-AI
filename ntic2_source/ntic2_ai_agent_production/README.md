# 🤖 Assistant ISTA NTIC - Documentation Complète

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Technologies Utilisées](#technologies-utilisées)
4. [Structure du Projet](#structure-du-projet)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Utilisation](#utilisation)
8. [API Documentation](#api-documentation)
9. [RAG Pipeline](#rag-pipeline)
10. [Agent Core](#agent-core)
11. [Déploiement](#déploiement)
12. [Troubleshooting](#troubleshooting)

---

## 🎯 Vue d'ensemble

**Assistant ISTA NTIC** est un système d'assistant intelligent basé sur l'IA pour l'Institut Spécialisé de Technologie Appliquée (ISTA) NTIC Sidi Maarouf. Le système utilise la technologie RAG (Retrieval-Augmented Generation) pour fournir des réponses précises basées sur les données du site web officiel de l'établissement.

### Fonctionnalités Principales

- ✅ **Chat intelligent multilingue** (Français, Anglais, Arabe, Espagnol)
- ✅ **RAG (Retrieval-Augmented Generation)** pour des réponses basées sur les données du site
- ✅ **Support multi-LLM** : Ollama (local), Groq (cloud), Hugging Face (cloud), OpenAI (cloud)
- ✅ **Mémoire conversationnelle** persistante avec PostgreSQL
- ✅ **Ingestion automatique** du contenu du site web
- ✅ **Interface utilisateur moderne** avec React
- ✅ **API RESTful** complète
- ✅ **Observabilité** avec logging détaillé

---

## 🏗️ Architecture

### Architecture Globale

```
┌─────────────────┐
│   Frontend      │  React + Vite
│   (Port 8080)   │
└────────┬────────┘
         │ HTTP/REST
         │
┌────────▼────────┐
│   Backend       │  Flask + Python
│   (Port 5000)   │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬─────────────┐
    │         │          │              │
┌───▼───┐ ┌──▼───┐ ┌────▼────┐ ┌───────▼──────┐
│PostgreSQL│ │ChromaDB│ │  Ollama   │ │  LLM APIs   │
│ (Memory) │ │  (RAG) │ │  (Local)  │ │ (Groq/HF)   │
└─────────┘ └───────┘ └──────────┘ └─────────────┘
```

### Flux de Données

1. **Requête Utilisateur** → Frontend (React)
2. **API Call** → Backend Flask (`/api/chat`)
3. **Agent Core** → Traitement de la requête
4. **RAG Pipeline** → Recherche dans ChromaDB
5. **LLM Provider** → Génération de la réponse
6. **PostgreSQL** → Sauvegarde de l'historique
7. **Réponse** → Frontend avec sources

---

## 🛠️ Technologies Utilisées

### Backend

#### Framework & Core
- **Python 3.11** - Langage de programmation
- **Flask 2.x** - Framework web léger
- **Werkzeug** - Utilitaires WSGI

#### Base de Données
- **PostgreSQL 15** - Base de données relationnelle pour la mémoire conversationnelle
- **psycopg2-binary** - Driver PostgreSQL pour Python
- **ChromaDB** - Base de données vectorielle pour RAG

#### IA & LLM
- **OpenAI** - API OpenAI (optionnel, payant)
- **Ollama** - LLM local gratuit (Llama 3.2, Mistral, etc.)
- **Groq API** - LLM cloud gratuit et rapide
- **Hugging Face Inference API** - LLM cloud gratuit
- **sentence-transformers** - Modèles d'embeddings locaux

#### RAG & Embeddings
- **ChromaDB** - Base de données vectorielle
- **BeautifulSoup4** - Parsing HTML
- **requests** - Requêtes HTTP
- **langchain** - Framework pour applications LLM

#### Traitement de Documents
- **PyPDF2** - Lecture de fichiers PDF
- **pdfplumber** - Extraction avancée de PDF
- **openpyxl** - Traitement de fichiers Excel
- **pandas** - Manipulation de données
- **Pillow** - Traitement d'images
- **pytesseract** - OCR (Optical Character Recognition)

#### Utilitaires
- **python-dotenv** - Gestion des variables d'environnement
- **logging** - Système de logs intégré

### Frontend

#### Framework & Build
- **React 18.2.0** - Bibliothèque UI
- **React DOM 18.2.0** - Rendu React
- **Vite 5.1.0** - Build tool et dev server
- **@vitejs/plugin-react** - Plugin React pour Vite

#### Styling
- **CSS3** - Styles personnalisés
- **Responsive Design** - Interface adaptative

### Infrastructure

#### Containerisation
- **Docker** - Containerisation
- **Docker Compose** - Orchestration multi-containers
- **Nginx** - Serveur web pour le frontend (production)

#### Services
- **PostgreSQL 15** - Base de données
- **Ollama** - Service LLM local
- **ChromaDB** - Service de base vectorielle

---

## 📁 Structure du Projet

```
ntic2_ai_agent_production/
│
├── backend/                    # Application backend Python
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # Point d'entrée Flask, routes API
│   │   ├── memory.py          # Gestion mémoire conversationnelle
│   │   │
│   │   ├── agent/             # Module agent IA
│   │   │   ├── __init__.py
│   │   │   └── core.py        # Cœur de l'agent (LLM, RAG, prompts)
│   │   │
│   │   ├── db/                # Module base de données
│   │   │   ├── __init__.py
│   │   │   ├── database.py    # Connexion PostgreSQL
│   │   │   └── seed.py        # Données initiales
│   │   │
│   │   ├── observability/     # Module observabilité
│   │   │   ├── __init__.py
│   │   │   └── logger.py      # Logging et monitoring
│   │   │
│   │   └── rag/              # Module RAG
│   │       ├── __init__.py
│   │       ├── ingest.py     # Ingestion du contenu web
│   │       └── pipeline.py    # Pipeline RAG (recherche, embeddings)
│   │
│   ├── Dockerfile             # Image Docker backend
│   ├── requirements.txt       # Dépendances Python
│   ├── check_and_ingest.py    # Script d'ingestion
│   └── diagnostic_systeme.py  # Script de diagnostic
│
├── frontend/                   # Application frontend React
│   ├── src/
│   │   ├── App.jsx            # Composant principal
│   │   ├── main.jsx           # Point d'entrée React
│   │   ├── styles.css         # Styles globaux
│   │   └── components/
│   │       └── Chat.jsx       # Composant chat
│   │
│   ├── Dockerfile             # Image Docker frontend (production)
│   ├── Dockerfile.dev         # Image Docker frontend (dev)
│   ├── nginx.conf             # Configuration Nginx
│   ├── package.json           # Dépendances Node.js
│   └── vite.config.js         # Configuration Vite
│
├── secrets/                    # Secrets (non versionnés)
│   ├── openai_api_key         # Clé API OpenAI
│   └── openai_api_key.txt     # Clé API OpenAI (backup)
│
├── chroma_db/                  # Base de données ChromaDB (générée)
│   └── chroma.sqlite3         # Fichier SQLite de ChromaDB
│
├── docker-compose.yml          # Configuration Docker Compose
├── .env                        # Variables d'environnement (non versionné)
├── env.example                 # Exemple de fichier .env
├── init.sql                    # Script d'initialisation PostgreSQL
├── init_ollama.sh             # Script d'initialisation Ollama
│
└── README.md                   # Cette documentation
```

---

## 🚀 Installation

### Prérequis

- **Docker** et **Docker Compose** installés
- **Git** pour cloner le projet
- **8GB RAM minimum** (recommandé 16GB pour Ollama)
- **Ports disponibles** : 5000 (backend), 8080 (frontend), 5432 (PostgreSQL), 11434 (Ollama)

### Installation avec Docker (Recommandé)

1. **Cloner le projet**
```bash
git clone <repository-url>
cd ntic2_ai_agent_production
```

2. **Configurer les variables d'environnement**
```bash
cp env.example .env
# Éditer .env avec vos clés API
```

3. **Configurer les secrets**
```bash
# Créer le fichier secrets/openai_api_key avec votre clé OpenAI
echo "votre_cle_openai" > secrets/openai_api_key
```

4. **Démarrer les services**
```bash
docker-compose up -d
```

5. **Initialiser Ollama (si utilisé)**
```bash
docker-compose exec ollama ollama pull llama3.2:latest
```

6. **Ingérer les données du site**
```bash
docker-compose exec backend python -m app.rag.ingest
```

### Installation Locale (Sans Docker)

#### Backend

1. **Installer Python 3.11+**
```bash
python --version  # Vérifier la version
```

2. **Créer un environnement virtuel**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer PostgreSQL**
   - Installer PostgreSQL 15
   - Créer la base de données `ntic2`
   - Exécuter `init.sql`

5. **Configurer les variables d'environnement**
```bash
# Créer .env à la racine du projet
OPENAI_API_KEY=votre_cle
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

6. **Démarrer le serveur**
```bash
cd backend
flask run --host=0.0.0.0 --port=5000
```

#### Frontend

1. **Installer Node.js 18+**
```bash
node --version  # Vérifier la version
```

2. **Installer les dépendances**
```bash
cd frontend
npm install
```

3. **Démarrer le serveur de développement**
```bash
npm run dev
```

4. **Build de production**
```bash
npm run build
```

---

## ⚙️ Configuration

### Variables d'Environnement (.env)

```env
# Provider LLM (ollama, groq, huggingface, openai)
LLM_PROVIDER=ollama

# Configuration Ollama (local, gratuit)
OLLAMA_BASE_URL=http://ollama:11434
# Pour usage local: http://localhost:11434

# Configuration Groq API (cloud, gratuit, rapide)
GROQ_API_KEY=votre_cle_groq

# Configuration Hugging Face (cloud, gratuit)
HF_API_KEY=votre_token_hf

# Configuration OpenAI (optionnel, payant)
OPENAI_API_KEY=votre_cle_openai

# Configuration PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=ntic2
POSTGRES_USER=ntic
POSTGRES_PASSWORD=ntic
```

### Configuration des LLM Providers

#### 1. Ollama (Recommandé - Local, Gratuit)

```bash
# Installer Ollama
# Windows: Télécharger depuis https://ollama.ai
# Linux/Mac: curl -fsSL https://ollama.ai/install.sh | sh

# Télécharger un modèle
ollama pull llama3.2:latest
# ou
ollama pull mistral:latest
```

**Avantages** :
- ✅ 100% gratuit
- ✅ Fonctionne hors ligne
- ✅ Données privées
- ✅ Pas de limite de requêtes

#### 2. Groq (Cloud, Gratuit, Rapide)

1. Créer un compte sur https://console.groq.com/
2. Générer une clé API
3. Ajouter dans `.env` : `GROQ_API_KEY=votre_cle`

**Avantages** :
- ✅ Gratuit avec quota généreux
- ✅ Très rapide (infrastructure optimisée)
- ✅ Pas d'installation locale

#### 3. Hugging Face (Cloud, Gratuit)

1. Créer un compte sur https://huggingface.co/
2. Générer un token sur https://huggingface.co/settings/tokens
3. Ajouter dans `.env` : `HF_API_KEY=votre_token`

**Avantages** :
- ✅ Gratuit
- ✅ Accès à de nombreux modèles
- ✅ Optionnel (fonctionne sans token mais avec rate limits)

#### 4. OpenAI (Cloud, Payant)

1. Créer un compte sur https://platform.openai.com/
2. Générer une clé API
3. Ajouter dans `.env` : `OPENAI_API_KEY=votre_cle`

**Avantages** :
- ✅ Modèles très performants (GPT-4, GPT-4o-mini)
- ✅ API stable et fiable

### Configuration ChromaDB

ChromaDB est automatiquement initialisé lors de la première ingestion. Les données sont stockées dans :
- **Docker** : `/app/chroma_db` (volume `chroma_data`)
- **Local** : `./chroma_db` à la racine du projet

### Configuration PostgreSQL

La base de données est initialisée automatiquement avec Docker Compose. Pour une installation locale :

```sql
CREATE DATABASE ntic2;
CREATE USER ntic WITH PASSWORD 'ntic';
GRANT ALL PRIVILEGES ON DATABASE ntic2 TO ntic;
```

Puis exécuter `init.sql` pour créer les tables.

---

## 💻 Utilisation

### Démarrage Rapide

1. **Démarrer tous les services**
```bash
docker-compose up -d
```

2. **Vérifier le statut**
```bash
docker-compose ps
```

3. **Voir les logs**
```bash
docker-compose logs -f backend
```

4. **Accéder à l'application**
   - Frontend : http://localhost:8080
   - Backend API : http://localhost:5000

### Ingestion des Données

L'ingestion récupère le contenu du site web ISTA NTIC et le stocke dans ChromaDB.

```bash
# Avec Docker
docker-compose exec backend python -m app.rag.ingest

# Local
cd backend
python -m app.rag.ingest
```

**Options d'ingestion** :
- `--update-only` : Met à jour uniquement les pages modifiées
- `--resume-from-backup` : Reprend depuis un backup

### Utilisation de l'API

#### Endpoint Chat

```bash
POST http://localhost:5000/api/chat
Content-Type: application/json

{
  "message": "Quels sont les emplois du temps disponibles ?",
  "user_id": "user123"
}
```

**Réponse** :
```json
{
  "reply": "Les emplois du temps sont disponibles...",
  "sources": [
    {
      "title": "ISTA NTIC SM - Emplois du temps",
      "section": "emplois-du-temps",
      "url": "https://sites.google.com/view/ista-ntic-sm/emplois-du-temps"
    }
  ],
  "status": {
    "chunks": 22,
    "connected": true
  },
  "rag_used": true,
  "chunk_count": 22,
  "sources_count": 1,
  "language": "fr"
}
```

#### Endpoint Status

```bash
GET http://localhost:5000/api/chat/status
```

#### Endpoint Clear

```bash
POST http://localhost:5000/api/chat/clear
Content-Type: application/json

{
  "user_id": "user123"
}
```

---

## 📚 API Documentation

### POST /api/chat

Envoie un message à l'assistant et reçoit une réponse.

**Request Body** :
```json
{
  "message": "string (requis)",
  "user_id": "string (optionnel, défaut: 'anon')"
}
```

**Response** :
```json
{
  "reply": "string - Réponse de l'assistant",
  "sources": [
    {
      "title": "string",
      "section": "string",
      "url": "string",
      "display": "string"
    }
  ],
  "status": {
    "chunks": "number",
    "connected": "boolean"
  },
  "rag_used": "boolean",
  "chunk_count": "number",
  "sources_count": "number",
  "language": "string (fr/en/ar/es)"
}
```

### GET /api/chat/status

Retourne le statut du système (nombre de chunks, connexion).

**Response** :
```json
{
  "chunks": 22,
  "connected": true,
  "status": "ok",
  "message": "22 chunks disponibles"
}
```

### POST /api/chat/clear

Efface l'historique de conversation pour un utilisateur.

**Request Body** :
```json
{
  "user_id": "string (requis)"
}
```

**Response** :
```json
{
  "status": "success",
  "message": "Conversation effacée"
}
```

---

## 🔍 RAG Pipeline

### Architecture RAG

Le système RAG (Retrieval-Augmented Generation) fonctionne en plusieurs étapes :

1. **Ingestion** (`rag/ingest.py`)
   - Scraping du site web ISTA NTIC
   - Parsing HTML avec BeautifulSoup
   - Extraction du contenu textuel
   - Découpage en chunks
   - Génération d'embeddings
   - Stockage dans ChromaDB

2. **Recherche** (`rag/pipeline.py`)
   - Requête utilisateur
   - Génération d'embedding de la requête
   - Recherche vectorielle dans ChromaDB
   - Récupération des chunks pertinents
   - Retour du contexte formaté

3. **Génération** (`agent/core.py`)
   - Injection du contexte RAG dans le prompt
   - Appel au LLM
   - Génération de la réponse
   - Formatage avec sources

### Embeddings

Le système supporte plusieurs méthodes d'embeddings :

1. **Ollama** (priorité 1) - Embeddings via modèle Ollama
2. **Sentence Transformers** (priorité 2) - Modèle local `paraphrase-multilingual-MiniLM-L12-v2`
3. **Hugging Face API** (priorité 3) - API gratuite
4. **OpenAI** (fallback) - `text-embedding-ada-002`

### Configuration RAG

Les paramètres RAG sont configurables dans `rag/pipeline.py` :

```python
# Nombre de résultats à retourner
n_results = 7  # Recommandé: 5-10

# Filtrage par section
filter_section = "emplois-du-temps"  # Optionnel
```

---

## 🤖 Agent Core

### Architecture de l'Agent

L'agent (`agent/core.py`) est le cœur du système. Il orchestre :

1. **Détection de langue** - Détecte automatiquement la langue de la requête
2. **Chargement de l'historique** - Récupère les messages précédents
3. **Récupération RAG** - Obtient le contexte pertinent
4. **Appel LLM** - Génère la réponse avec fallback automatique
5. **Nettoyage** - Supprime les répétitions et formate la réponse
6. **Sauvegarde** - Stocke l'échange dans PostgreSQL

### Prompt Système

Le prompt système (`SYSTEM_PROMPT`) définit le comportement de l'agent :

- ✅ Réponses uniquement basées sur les données RAG
- ✅ Format détaillé, propre, simple et spécifique
- ✅ Support multilingue
- ✅ Intégration des sources et URLs
- ✅ Section SOURCES obligatoire

### Fallback Intelligent

Si le LLM n'est pas disponible, le système utilise un fallback intelligent qui :
- Extrait les informations pertinentes du contexte RAG
- Formate la réponse de manière structurée
- Inclut les sources

---

## 🚢 Déploiement

### Déploiement avec Docker Compose

1. **Production**
```bash
docker-compose -f docker-compose.yml up -d
```

2. **Développement**
```bash
docker-compose up frontend-dev backend postgres
```

### Déploiement sur Serveur

1. **Cloner le projet sur le serveur**
```bash
git clone <repository-url>
cd ntic2_ai_agent_production
```

2. **Configurer les variables d'environnement**
```bash
cp env.example .env
nano .env  # Éditer avec vos configurations
```

3. **Démarrer les services**
```bash
docker-compose up -d
```

4. **Configurer Nginx (optionnel)**
```nginx
server {
    listen 80;
    server_name votre-domaine.com;

    location / {
        proxy_pass http://localhost:8080;
    }

    location /api {
        proxy_pass http://localhost:5000;
    }
}
```

### Variables d'Environnement Production

```env
# Sécurité
FLASK_ENV=production
DEBUG=False

# LLM Provider
LLM_PROVIDER=groq  # Recommandé pour production (rapide)

# Base de données
POSTGRES_PASSWORD=password_securise
```

---

## 🔧 Troubleshooting

### Problèmes Courants

#### 1. Erreur "Aucun provider LLM disponible"

**Solution** :
- Vérifier que Ollama est démarré : `docker-compose ps ollama`
- Vérifier les clés API dans `.env`
- Vérifier les logs : `docker-compose logs backend`

#### 2. ChromaDB vide ou erreur de collection

**Solution** :
```bash
# Réingérer les données
docker-compose exec backend python -m app.rag.ingest
```

#### 3. PostgreSQL non accessible

**Solution** :
```bash
# Vérifier que PostgreSQL est démarré
docker-compose ps postgres

# Vérifier les logs
docker-compose logs postgres

# Recréer la base de données si nécessaire
docker-compose down -v
docker-compose up -d postgres
```

#### 4. Ollama timeout

**Solution** :
- Augmenter le timeout dans `agent/core.py`
- Vérifier que le modèle est téléchargé : `ollama list`
- Télécharger le modèle : `ollama pull llama3.2:latest`

#### 5. Frontend ne se connecte pas au backend

**Solution** :
- Vérifier que le backend est accessible : `curl http://localhost:5000`
- Vérifier CORS dans `main.py`
- Vérifier les URLs dans `frontend/src/components/Chat.jsx`

### Logs et Debugging

#### Voir les logs en temps réel
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

#### Logs spécifiques
```bash
# Logs backend uniquement
docker-compose logs backend | grep ERROR

# Logs RAG
docker-compose logs backend | grep RAG
```

#### Diagnostic système
```bash
# Script de diagnostic
docker-compose exec backend python diagnostic_systeme.py
```

### Performance

#### Optimisations Recommandées

1. **ChromaDB** : Utiliser un nombre de résultats adapté (5-7)
2. **LLM** : Utiliser Groq pour la vitesse
3. **Embeddings** : Utiliser Ollama pour la cohérence
4. **PostgreSQL** : Indexer les colonnes fréquemment utilisées

#### Monitoring

- **Chunks disponibles** : `GET /api/chat/status`
- **Logs** : `docker-compose logs`
- **Ressources** : `docker stats`

---

## 📊 Métriques et Observabilité

### Logs

Le système génère des logs détaillés :
- **INFO** : Opérations normales
- **WARNING** : Problèmes non critiques
- **ERROR** : Erreurs nécessitant attention

### Métriques Disponibles

- Nombre de chunks dans ChromaDB
- Nombre de sources par réponse
- Langue détectée
- Provider LLM utilisé
- Temps de réponse

---

## 🔐 Sécurité

### Bonnes Pratiques

1. **Ne jamais commiter les secrets**
   - `.env` doit être dans `.gitignore`
   - `secrets/` doit être dans `.gitignore`

2. **Utiliser des mots de passe forts**
   - PostgreSQL : changer le mot de passe par défaut
   - API Keys : régénérer régulièrement

3. **Limiter l'accès**
   - Utiliser un firewall
   - Limiter les ports exposés
   - Utiliser HTTPS en production

4. **Mettre à jour régulièrement**
   - Docker images
   - Dépendances Python
   - Dépendances Node.js

---

## 📝 Contribution

### Structure de Code

- **Backend** : PEP 8 (Python style guide)
- **Frontend** : ESLint + Prettier
- **Commits** : Messages clairs et descriptifs

### Tests

```bash
# Tests backend
cd backend
python test_functionnalites.py

# Tests unitaires
python test_unitaire.py
```

---

## 📄 Licence

Ce projet est propriétaire et destiné à l'usage interne de l'ISTA NTIC.

---

## 👥 Support

Pour toute question ou problème :
- **Email** : istanticsm@gmail.com
- **Documentation** : Ce fichier README.md
- **Logs** : Vérifier les logs Docker

---

## 🎯 Roadmap

### Améliorations Futures

- [ ] Support de plus de langues
- [ ] Amélioration de la détection de section
- [ ] Cache des réponses fréquentes
- [ ] Interface d'administration
- [ ] Analytics et métriques avancées
- [ ] Support de fichiers PDF/Word dans RAG
- [ ] Mode hors ligne complet
- [ ] Intégration avec d'autres systèmes

---

**Dernière mise à jour** : 2024
**Version** : 1.0.0
**Auteur** : Équipe ISTA NTIC
