from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.user import router as user_router
from app.api.files import router as files_router
from app.api.seat import router as seat_router
from app.api.book import router as book_router
from app.api.ai import router as ai_router

api = APIRouter(prefix="/api")

api.include_router(auth_router)
api.include_router(user_router)
api.include_router(files_router)
api.include_router(seat_router)
api.include_router(book_router)
api.include_router(ai_router)
