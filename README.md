# Smart Presence AI

Full-stack intelligent attendance system with facial recognition, real-time tracking, and AI chatbot support.

## 🚀 Features

### 🤖 AI Chatbot
- **Multi-provider LLM**: Groq, Gemini, OpenAI with automatic fallbacks
- **RAG Pipeline**: ChromaDB with Smart Presence knowledge base
- **Streaming Responses**: Real-time chat with Server-Sent Events
- **Memory Management**: PostgreSQL-based conversation history

### 👤 Facial Recognition
- **Advanced Recognition**: Vector-based matching with pgvector
- **Liveness Detection**: Anti-spoofing with photo validation
- **Multiple Check-in Methods**: Facial recognition + QR codes
- **Secure Storage**: Encrypted facial embeddings

### 🔄 N8N Automation
- **5 Workflows**: Email notifications, exam reminders, WhatsApp alerts
- **Real-time Webhooks**: Instant automation triggers
- **PDF Reports**: Daily absence reports with Gotenberg
- **AI Scoring**: Automatic attendance analysis

### 📱 Modern Frontend
- **Next.js 14**: App Router, TypeScript, Tailwind CSS
- **Responsive Design**: Mobile-first approach
- **Real-time Updates**: WebSocket integration
- **Interactive Dashboard**: Analytics and insights

## 🏗️ Architecture

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL + pgvector, Redis
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind
- **Infrastructure**: Docker Compose (backend, frontend, db, cache, gotenberg)
- **AI**: Multi-provider LLM with ChromaDB RAG
- **Automation**: N8N workflows with webhook integration

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- API Keys (GROQ_API_KEY, GOOGLE_API_KEY, or OPENAI_API_KEY)

### Setup

```bash
# Clone the repository
git clone https://github.com/20Hanae20/-Smart-Present-AI.git
cd -Smart-Present-AI

# Configure environment
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Add your API keys to .env files
# GROQ_API_KEY=your_groq_key
# GOOGLE_API_KEY=your_gemini_key
# OPENAI_API_KEY=your_openai_key

# Start all services
docker-compose up -d --build

# Seed AI knowledge base
docker-compose exec backend python -m app.scripts.seed_chromadb
```

### Access Points
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **AI Chatbot**: http://localhost:3000/chat
- **PDF Service**: http://localhost:3001

## 📋 Project Structure

```
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── ai_agent/      # AI chatbot components
│   │   ├── api/          # REST API routes
│   │   ├── models/       # Database models
│   │   ├── services/      # Business logic
│   │   └── scripts/      # Utility scripts
│   ├── alembic/          # Database migrations
│   └── requirements.txt   # Python dependencies
├── frontend/               # Next.js application
│   ├── app/              # App Router pages
│   ├── components/        # React components
│   ├── lib/              # Utilities
│   └── package.json      # Node.js dependencies
├── scripts/               # Helper scripts
├── docker-compose.yml     # Container orchestration
└── PRESENTATION_SCRIPT.md # Demo presentation
```

## 🔧 Development

### Backend Development
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd frontend
npm ci
npm run dev
```

## 🔐 Environment Variables

### Backend (.env)
```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/smartpresence
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# AI Configuration (at least one required)
GROQ_API_KEY=your_groq_key
GOOGLE_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key

# Optional
REDIS_CACHE_ENABLED=true
N8N_WEBHOOK_URL=http://localhost:5678/webhook
```

### Frontend (.env)
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NODE_ENV=development
```

## 🤖 AI Chatbot Usage

### Endpoints
- **Status**: `GET /api/chatbot/status`
- **Chat**: `POST /api/chatbot/ask`
- **Streaming**: `POST /api/chatbot/stream`
- **History**: `GET /api/chatbot/history/{user_id}`

### Example Usage
```javascript
// Streaming chat
const response = await fetch('/api/chatbot/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Comment faire le check-in?',
    user_id: 'user123'
  })
});

const reader = response.body.getReader();
// Process streaming chunks...
```

## 🔄 N8N Integration

### Available Workflows
1. **Absence Email**: Automatic parent notifications
2. **Exam Reminders**: 72-hour advance warnings
3. **WhatsApp Alerts**: >8h absence notifications
4. **AI Scoring**: Attendance analysis with AI
5. **Daily Reports**: PDF generation and distribution

### Setup
```bash
# Import enhanced workflows
# Import scripts/enhanced-n8n-workflows.json into N8N

# Configure webhooks
# Point N8N webhooks to: http://localhost:8000/api/n8n
```

## 📊 Features in Detail

### Facial Recognition System
- **Vector Database**: pgvector for efficient similarity search
- **Multi-photo Registration**: 3 photos per student for accuracy
- **Liveness Detection**: Prevents photo spoofing attacks
- **Real-time Processing**: Sub-second recognition response

### Attendance Management
- **Multiple Check-in Methods**: Facial, QR code, manual
- **Session Management**: Flexible session scheduling
- **Real-time Tracking**: Live attendance monitoring
- **Automated Statistics**: Automatic rate calculations

### AI Chatbot
- **Context Awareness**: Remembers conversation history
- **Knowledge Integration**: Access to system documentation
- **Multi-language Support**: French and English
- **Fallback Systems**: Multiple LLM providers

## 🧪 Testing

### Backend Tests
```bash
# Run all tests
docker-compose exec backend pytest

# Run specific test
docker-compose exec backend pytest tests/test_auth.py
```

### Frontend Tests
```bash
cd frontend
npm run test
npm run test:e2e
```

## 📈 Monitoring

### Health Checks
- **Backend**: `GET /health`
- **Metrics**: `GET /metrics/summary`
- **Chatbot**: `GET /api/chatbot/status`

### Logs
```bash
# View all logs
./scripts/logs.sh

# View specific service
./scripts/logs.sh backend
./scripts/logs.sh frontend
```

## 🚀 Deployment

### Production Deployment
1. **Configure Environment**: Set production secrets
2. **Database Setup**: Configure PostgreSQL with pgvector
3. **SSL Configuration**: Set up HTTPS certificates
4. **N8N Setup**: Configure automation workflows
5. **Monitoring**: Set up logging and metrics

### Docker Production
```bash
# Build and deploy
docker-compose -f docker-compose.prod.yml up -d

# Scale services
docker-compose up -d --scale backend=3 --scale frontend=2
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- 📧 Email: support@smartpresence.ai
- 📖 Documentation: Check `/docs` in the application
- 🐛 Issues: Create an issue on GitHub

---

**Built with ❤️ for modern education management**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

Helper scripts (repo root):
- `./scripts/start.sh` — start all services
- `./scripts/stop.sh` — stop services
- `./scripts/status.sh` — check container and port health
- `./scripts/logs.sh [service]` — follow logs (all or per service)
- `./scripts/migrate.sh` — run Alembic migrations
- `./scripts/create-admin.sh` — interactive admin creation
- `./scripts/seed-demo.sh` — load demo data (users, sessions, faces)
- `./scripts/reset-docker.sh` — clean reset if you need a fresh slate

## Demo Accounts (from seed)
- Admin: `badr.eddine.boudhim@smartpresence.com` / `Luno.xar.95`
- Trainers: `dam.nachit@smartpresence.com`, `yassin.madani@smartpresence.com`, `rachid.aitaamou@smartpresence.com` / `Trainer.123`
- Students: `taha.khebazi@smartpresence.com`, `walid.eltahiri@smartpresence.com`, `sara.aitaamou@smartpresence.com`, `karim.bennani@smartpresence.com`, `amine.elalami@smartpresence.com` / `Student.123`

## Features
- Facial recognition with liveness and vector matching (pgvector)
- Multi-role dashboards (admin, trainer, student)
- Session requests/approvals, QR and facial check-in
- Real-time notifications/chat (websocket)
- Exports (PDF/CSV), analytics, and fraud review

## Structure
```
backend/   # FastAPI app (routes, services, models, schemas)
frontend/  # Next.js app (App Router, components, pages)
docs/      # Project and deployment docs
scripts/   # Helper scripts for docker, seeds, admin, migrations
```

## Development (local, optional)
Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm ci
npm run dev
```

## Tests
- Backend: `./scripts/test.sh` (docker) or `docker-compose exec backend pytest`
- Frontend e2e: `cd frontend && npm run test:e2e`

## Notes
- Copy `.env.example` files and set strong secrets before production.
- Docker is the preferred way to run; local mode expects PostgreSQL + Redis available.
- See `docs/` and `scripts/README.md` for detailed operations and deployment.
- Do **not** version or pull generated artifacts: `chroma_db/**`, `backend/chroma_db/**`, `*.sqlite3`, `backend/storage/faces/**`, `ntic2_source/secrets/**`, other secrets. Regenerate locally by running migrations/seeds and the RAG ingestion script: `docker-compose exec backend python backend/scripts/ingest_ista_knowledge.py` (or equivalent seed). Keep secrets in `.env` files only.
=======
# -Smart-Present-AI
 Smart-Present-AI
>>>>>>> 0cb91cb0483665f2a00a46d704b4fa38bc544c2e
