# LexQuery

**AI-powered legal document intelligence for legal professionals.**

LexQuery lets you upload contracts, briefs, and regulations, ask questions in plain English, and get cited answers with exact page references and confidence scores — grounded entirely in your documents, never hallucinated.

> Built from scratch without LangChain. Custom hybrid retrieval pipeline, multi-tenant SaaS architecture, and enterprise-grade access controls.

---

## What it does

Legal professionals spend an enormous amount of time searching through documents they didn't write. LexQuery solves that.

- Upload a PDF, Word document, or paste a public URL
- Ask any question in plain English
- Get a cited answer with the exact page it came from and a confidence score
- Ask follow-up questions — conversation memory keeps the context

Every answer is grounded in your documents. No guessing, no hallucination.

---

## Features

### Core
- **Hybrid RAG retrieval** — vector similarity + BM25 full-text search, fused with reciprocal rank fusion and a reranking layer
- **Cited answers** — every claim links back to its exact source passage and page number
- **Confidence scoring** — High / Medium / Low / Insufficient rated on every response
- **Conversation memory** — multi-turn queries with session context
- **Document viewer** — read PDFs, Word docs, and text files inline without leaving the app
- **@ mention** — type `@` or `/` in the query input to scope a question to a specific document

### Access & security
- **Multi-tenant isolation** — organisations are fully isolated at the database level
- **Role-based access** — Viewer, Editor, Matter Admin, Tenant Admin
- **Document permissions** — restrict individual documents to specific roles, enforced at query time not just the UI
- **JWT authentication** with Google OAuth and TOTP two-factor authentication
- **Audit log** — every query logged with user, answer, confidence score, and cited documents

### Infrastructure
- **Async document ingestion** — Celery + Redis background processing, no upload blocking
- **LLM fallback chain** — Groq → Anthropic Claude → OpenAI, so the system never goes down if one provider has an outage
- **AWS S3** — document storage with presigned URL viewer
- **Stripe billing** — trial, Starter, Professional, Enterprise plans
- **GDPR data erasure** — full tenant data deletion on request

### Admin
- Team member management with role assignment
- Document permission management per workspace
- Audit log viewer with search, pagination, and CSV export
- Organisation logo upload and profile management
- Usage bars for queries, pages indexed, and seats

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.11) |
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Database | PostgreSQL + SQLAlchemy (async) |
| Vector store | Weaviate |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Reranking | Cohere rerank-english-v3.0 |
| LLM | Groq (llama-3.3-70b) → Anthropic Claude → OpenAI |
| Task queue | Celery + Redis |
| File storage | AWS S3 (eu-west-2) |
| Auth | JWT, bcrypt, Google OAuth, TOTP (pyotp) |
| Billing | Stripe |
| Email | Gmail SMTP |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Next.js Frontend                     │
│          Dashboard · Admin Panel · Settings              │
└─────────────────────┬───────────────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────────────┐
│                    FastAPI Backend                        │
│  Auth · Documents · Query · Workspaces · Billing · Audit │
└──────┬──────────────┬──────────────┬─────────────────────┘
       │              │              │
┌──────▼───┐   ┌──────▼───┐   ┌─────▼──────┐
│PostgreSQL│   │ Weaviate │   │   Redis    │
│ metadata │   │  chunks  │   │task queue  │
└──────────┘   └──────────┘   └─────┬──────┘
                                     │
                              ┌──────▼──────┐
                              │Celery Worker│
                              │  ingestion  │
                              └─────────────┘
```

---

## Retrieval pipeline

```
Query
  │
  ├── Vector search (cosine similarity, Weaviate)
  ├── BM25 full-text search (Weaviate)
  │
  ├── Reciprocal Rank Fusion (merge + rerank candidates)
  ├── Cohere Rerank (semantic relevance scoring)
  │
  ├── Permission filter (role-based, enforced from PostgreSQL)
  │
  └── LLM generation (Groq → Anthropic → OpenAI fallback)
        │
        └── Cited answer + confidence score
```

---

## Monorepo structure

```
lexquery/
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── api/v1/endpoints/ # All route handlers
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   └── workers/          # Celery tasks
│   ├── migrations/           # Alembic migrations
│   └── requirements.txt
├── frontend/                 # Next.js application
│   ├── app/
│   │   ├── dashboard/        # Main app
│   │   ├── dashboard/admin/  # Admin panel
│   │   └── dashboard/settings/
│   └── lib/                  # API client, auth context
├── infra/
│   ├── docker/               # Dockerfiles
│   └── terraform/            # AWS IaC (Phase 2)
└── .github/
    └── workflows/            # CI pipelines
```

---

## Quick start (local dev)

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop (for PostgreSQL, Redis, Weaviate)

### 1. Clone and configure

```bash
git clone https://github.com/Iammteo/lexQuery.git
cd lexquery
cp backend/.env.example backend/.env
# Fill in your API keys — see Environment variables below
```

### 2. Start infrastructure

```bash
docker compose up -d
```

Starts PostgreSQL, Redis, and Weaviate locally.

### 3. Run database migrations

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
```

### 4. Start the backend

```bash
# Terminal 1 — API
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0

# Terminal 2 — Celery worker
TOKENIZERS_PARALLELISM=false celery -A app.workers.celery_app worker \
  --loglevel=info --queues=ingestion --pool=solo
```

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Weaviate | http://localhost:8080 |

---

## Environment variables

Create `backend/.env` with the following:

```env
# Core
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql+asyncpg://lexquery:lexquery_dev@localhost:5432/lexquery
DATABASE_URL_SYNC=postgresql://lexquery:lexquery_dev@localhost:5432/lexquery

# LLM providers (cascading fallback — at least one required)
GROQ_API_KEY=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Embeddings + reranking
# sentence-transformers runs locally — no key needed
COHERE_API_KEY=          # optional, improves reranking quality

# Storage
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=eu-west-2
S3_BUCKET_NAME=

# Auth
GMAIL_USER=
GMAIL_APP_PASSWORD=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/v1/auth/google/callback

# Billing
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_STARTER_PRICE_ID=
STRIPE_PROFESSIONAL_PRICE_ID=
STRIPE_ENTERPRISE_PRICE_ID=

# Redis
REDIS_URL=redis://localhost:6379/0
```

---

## Why no LangChain

LangChain is a good tool for shipping RAG quickly. It abstracts the pipeline in ways that make it hard to understand exactly what is happening at each stage — why a particular chunk was retrieved, what the model is actually receiving as context, where retrieval is failing.

This project was built to understand RAG at that level. Every component of the retrieval pipeline is written from scratch: chunking, embedding, hybrid search, RRF fusion, reranking, permission filtering, and LLM generation. The result is a system where every failure mode is visible and every optimisation is deliberate.

---

## Roadmap

- [ ] pgvector migration (remove Weaviate dependency for free hosting)
- [ ] Microsoft OAuth + SSO/SAML
- [ ] Semantic query caching
- [ ] Streaming LLM responses
- [ ] Matter-level workspaces
- [ ] Public API with API key authentication

---

## Licence

MIT
