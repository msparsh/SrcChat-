import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.session import init_db
from app.api.endpoints import router as api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("srcchat")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schema and vector extension...")
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.warning(f"Database initialization warning (will retry on incoming requests if DB starts up late): {e}")
    yield
    logger.info("SrcChat shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Agentic codebase assistant for public GitHub repositories",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error handling {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "An internal server error occurred.", "detail": str(exc)}
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
