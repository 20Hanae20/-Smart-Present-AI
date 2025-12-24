docker-compose exec backend python3 -c "
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
db = SessionLocal()
db.add(admin)
db.commit()
db.close()
# Smart Presence AI

Full-stack intelligent attendance system with facial recognition, real-time tracking, and chatbot support.

- Backend: FastAPI, SQLAlchemy, PostgreSQL + pgvector, Redis
- Frontend: Next.js 14 (App Router), TypeScript, Tailwind
- Infra: Docker Compose (backend, frontend, db, cache)

## Quick Start (Docker)

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

docker-compose up -d --build
```

Services:
- Frontend: http://localhost:3000
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
