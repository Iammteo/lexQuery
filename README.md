# LexQuery

Enterprise Legal Intelligence Platform — AI-powered RAG for legal professionals.

## Monorepo structure

```
lexquery/
├── backend/        # FastAPI application (Python)
├── frontend/       # Next.js web app + admin console (TypeScript)
├── infra/
│   ├── docker/     # Dockerfiles
│   └── terraform/  # AWS IaC (Phase 2)
└── .github/
    └── workflows/  # CI pipelines
```

## Quick start (local dev)

### Prerequisites
- Docker Desktop
- Python 3.11+
- Node.js 20+

### 1. Clone and configure environment
```bash
git clone <repo>
cd lexquery
cp backend/.env.example backend/.env
# Fill in your API keys in backend/.env
```

### 2. Start infrastructure
```bash
docker compose up -d
```
This starts: PostgreSQL, Redis, Weaviate.

### 3. Run database migrations
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
```

### 4. Start the API
```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Start the frontend
```bash
cd frontend
npm install
npm run dev
```

API docs available at: http://localhost:8000/docs  
Frontend at: http://localhost:3000

## Services (local ports)

| Service    | Port  |
|------------|-------|
| FastAPI    | 8000  |
| Next.js    | 3000  |
| PostgreSQL | 5432  |
| Redis      | 6379  |
| Weaviate   | 8080  |
