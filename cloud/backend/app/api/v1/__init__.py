"""
ApexAurum Cloud - API v1 Router

All API endpoints are mounted here.
"""

from fastapi import APIRouter

from app.api.v1 import auth, chat, agents, village, tools, music, user

router = APIRouter()

# Include sub-routers
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(chat.router, prefix="/chat", tags=["Chat"])
router.include_router(agents.router, prefix="/agents", tags=["Agents"])
router.include_router(village.router, prefix="/village", tags=["Village"])
router.include_router(tools.router, prefix="/tools", tags=["Tools"])
router.include_router(music.router, prefix="/music", tags=["Music"])
router.include_router(user.router, prefix="/user", tags=["User"])
