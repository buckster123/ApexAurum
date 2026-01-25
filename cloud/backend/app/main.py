"""
ApexAurum Cloud - Main FastAPI Application

The cloud-native version of ApexAurum.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db, close_db
from app.api.v1 import router as api_v1_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("=" * 50)
    print("ApexAurum Cloud v5 - WITH CLAUDE INTEGRATION")
    print("=" * 50)
    await init_db()
    print("Database initialized - FRESH BUILD")

    yield

    # Shutdown
    print("Shutting down...")
    await close_db()
    print("Database closed")


# Create FastAPI app
app = FastAPI(
    title="ApexAurum Cloud",
    description="""
    Production-grade AI interface with multi-agent orchestration,
    persistent memory, and 140+ integrated tools.

    ## Features

    - **Chat**: Stream responses from Claude with tool execution
    - **Agents**: Spawn background agents for complex tasks
    - **Village**: Multi-agent shared memory with convergence detection
    - **Tools**: 140+ tools for files, code, web, music, and more
    - **Music**: AI music generation via Suno

    ## Authentication

    All endpoints require JWT Bearer authentication except `/health` and `/auth/*`.
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check (no auth required)
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for load balancers."""
    return {"status": "healthy", "version": "0.1.0"}


# Root redirect to docs
@app.get("/", include_in_schema=False)
async def root():
    """Redirect to API documentation."""
    return JSONResponse(
        content={
            "message": "ApexAurum Cloud API",
            "docs": "/docs",
            "health": "/health",
        }
    )


# Mount API v1 router
app.include_router(api_v1_router, prefix="/api/v1")


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
        }
    )
