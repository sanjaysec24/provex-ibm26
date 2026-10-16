from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.models.schemas import HealthResponse
from app.api.routes_gateway import router as gateway_router
from app.api.routes_audit import router as audit_router

app = FastAPI(
    title="PROVEX AI Security Gateway",
    description="Deterministic Zero-Trust AI Security Gateway & Audit System (IBM Z Datathon 2026)",
    version="0.1.0"
)

# CORS configuration for local React Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(gateway_router)
app.include_router(audit_router)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Return runtime health status and operational parameters."""
    return HealthResponse(
        status="healthy",
        environment=settings.PROVEX_ENV,
        data_adapter=settings.PROVEX_DATA_ADAPTER,
        policy_engine_active=True
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.PROVEX_HOST,
        port=settings.PROVEX_PORT,
        reload=True
    )
