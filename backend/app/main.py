"""Main FastAPI application"""

from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.core.config import settings
from backend.app.octostrator.graphs import MainGraph

# Global graph instance
main_graph: Optional[MainGraph] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global main_graph

    # Startup
    logger.info("Starting Octostrator application")

    # Initialize main graph
    main_graph = MainGraph()
    await main_graph.initialize()
    logger.info("Main graph initialized")

    yield

    # Shutdown
    logger.info("Shutting down Octostrator application")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env
    }


# Import and include API routes
from backend.app.api.v1 import chat, todos, sessions, websocket

app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(todos.router, prefix="/api/v1", tags=["todos"])
app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
        log_level=settings.log_level.lower()
    )