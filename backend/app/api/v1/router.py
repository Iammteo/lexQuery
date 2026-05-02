from fastapi import APIRouter
from app.api.v1.endpoints import (
    health, documents, query, workspaces, audit,
    auth, oauth, users, billing, api_keys,
    password_reset, feedback
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(oauth.router, prefix="/auth", tags=["oauth"])
api_router.include_router(password_reset.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])