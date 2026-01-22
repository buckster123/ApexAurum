"""
Apex Aurum - Lab Edition

A clean, async-native scaffold for building AI applications.
Uses the reusable_lib modules for all AI functionality.
Part of the Apex Aurum ecosystem.

Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8765

Or for production:
    gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app_config import settings
from routes import chat, tools, models, memory, benchmark, conversations, stats, presets, village, prompts
from routes import websocket as ws_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info(f"Starting Apex Aurum - Lab Edition on {settings.HOST}:{settings.PORT}")
    logger.info(f"Default model: {settings.DEFAULT_MODEL}")
    logger.info(f"LLM endpoint: {settings.LLM_BASE_URL}")
    yield
    # Shutdown
    logger.info("Shutting down Apex Aurum - Lab Edition")


# Create app
app = FastAPI(
    title="Apex Aurum - Lab Edition",
    description="Alchemical AI experimentation platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware (allow all for local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
static_path = Path(__file__).parent / "static"
templates_path = Path(__file__).parent / "templates"

app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(tools.router, prefix="/api/tools", tags=["Tools"])
app.include_router(models.router, prefix="/api/models", tags=["Models"])
app.include_router(memory.router, prefix="/api/memory", tags=["Memory"])
app.include_router(benchmark.router, prefix="/api/benchmark", tags=["Benchmark"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["Conversations"])
app.include_router(stats.router, prefix="/api/stats", tags=["Statistics"])
app.include_router(presets.router, prefix="/api/presets", tags=["Presets"])
app.include_router(village.router, tags=["Village Protocol"])
app.include_router(prompts.router, prefix="/api/prompts", tags=["Prompts"])
app.include_router(ws_routes.router, prefix="/ws", tags=["WebSocket"])

# Mount Village GUI static files
village_static = Path(__file__).parent / "static" / "village"
village_static.mkdir(parents=True, exist_ok=True)
app.mount("/village", StaticFiles(directory=village_static, html=True), name="village")


@app.get("/")
async def index(request: Request):
    """Serve the main UI."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Apex Aurum - Lab Edition",
        "default_model": settings.DEFAULT_MODEL
    })


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/api")
async def api_info():
    """API information."""
    return {
        "name": "Apex Aurum - Lab Edition API",
        "version": "1.0.0",
        "phase": "9 - Village GUI",
        "endpoints": {
            "chat": "/api/chat",
            "stream": "/api/chat/stream",
            "tools": "/api/tools",
            "models": "/api/models",
            "memory": "/api/memory",
            "benchmark": "/api/benchmark",
            "conversations": "/api/conversations",
            "stats": "/api/stats",
            "presets": "/api/presets",
            "village": "/api/village",
            "websocket": "/ws/village",
            "village_gui": "/village/"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
