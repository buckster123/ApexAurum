# ApexAurum Cloud

The cloud-native version of ApexAurum - scalable, multi-user, production-ready.

```
"The gold was always there. Now we share it with the world."
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for frontend development)
- Python 3.11+ (for backend development)

### Development Setup

```bash
# 1. Copy environment file
cp backend/.env.example backend/.env
# Edit backend/.env with your ANTHROPIC_API_KEY

# 2. Start all services
docker-compose -f docker-compose.dev.yml up

# Services will be available at:
# - Frontend: http://localhost:3000
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Adminer (DB GUI): http://localhost:8080 (with --profile tools)
```

### Local Development (without Docker)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Architecture

```
cloud/
├── backend/               # FastAPI application
│   ├── app/
│   │   ├── main.py       # FastAPI app entry
│   │   ├── config.py     # Settings from env
│   │   ├── database.py   # Async SQLAlchemy
│   │   ├── api/v1/       # API routes
│   │   ├── auth/         # JWT authentication
│   │   ├── models/       # SQLAlchemy models
│   │   ├── services/     # Business logic
│   │   └── tools/        # Tool implementations
│   ├── alembic/          # Database migrations
│   └── tests/
├── frontend/              # Vue.js SPA
│   ├── src/
│   │   ├── views/        # Page components
│   │   ├── components/   # Reusable components
│   │   ├── stores/       # Pinia state
│   │   ├── services/     # API client
│   │   └── router/       # Vue Router
│   └── public/
├── infrastructure/        # DevOps configs
│   ├── k8s/              # Kubernetes manifests
│   └── terraform/        # Cloud provisioning
└── docs/                  # Documentation
    └── ARCHITECTURE.md   # Detailed architecture
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/auth/login` | Login |
| `POST /api/v1/auth/register` | Register |
| `POST /api/v1/chat/message` | Send message (streaming) |
| `GET /api/v1/chat/conversations` | List conversations |
| `POST /api/v1/agents/spawn` | Spawn agent |
| `POST /api/v1/agents/council` | Socratic council |
| `GET /api/v1/village/knowledge` | Search knowledge |
| `POST /api/v1/music/generate` | Generate music |
| `GET /api/v1/tools/` | List tools |

Full API docs at: http://localhost:8000/docs

## Database

PostgreSQL with pgvector for embeddings.

```bash
# Run migrations
cd backend
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

## Tech Stack

### Backend
- FastAPI (async Python)
- SQLAlchemy 2.0 (async ORM)
- PostgreSQL + pgvector
- Redis (cache/sessions)
- Alembic (migrations)
- ARQ (background tasks)

### Frontend
- Vue 3 + Composition API
- Pinia (state management)
- TailwindCSS
- Vite

### Infrastructure
- Docker & Docker Compose
- Kubernetes (production)
- Terraform (cloud provisioning)

## Comparison with Streamlit Version

| Feature | Streamlit | Cloud |
|---------|-----------|-------|
| Users | Single | Multi |
| Auth | None | JWT |
| Database | JSON files | PostgreSQL |
| Scaling | Vertical | Horizontal |
| Sessions | Memory | Redis |
| Deployment | Manual | Docker/K8s |

## Development Roadmap

- [x] Architecture design
- [x] Backend scaffold (FastAPI, models, auth)
- [x] Frontend scaffold (Vue.js, router, stores)
- [x] Docker Compose dev environment
- [ ] Complete API endpoints
- [ ] Port 140 tools
- [ ] Vue.js views (Chat, Village, etc.)
- [ ] WebSocket streaming
- [ ] Kubernetes manifests
- [ ] CI/CD pipeline
- [ ] Production deployment

## Contributing

1. Create feature branch
2. Make changes
3. Run tests: `pytest backend/tests/`
4. Submit PR

---

*Part of the ApexAurum project - 140 Tools. Five Minds. One Village.*
