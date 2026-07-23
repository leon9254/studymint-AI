from fastapi import APIRouter

from app.api.routes import admin, auth, documents, integrations, pdf_exports, stuvia_agent, templates, tenants, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(pdf_exports.router, prefix="/pdf-exports", tags=["pdf exports"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(stuvia_agent.router, prefix="/stuvia-agent", tags=["stuvia agent"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
