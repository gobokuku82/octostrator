"""FastAPI Application Entry Point"""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

from .routes import agent_router, websocket_router, health_router

# Dashboard paths
DASHBOARD_DIR = Path(__file__).parent.parent.parent / "dashboard"
TEMPLATES_DIR = DASHBOARD_DIR / "templates"
STATIC_DIR = DASHBOARD_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting Dream Agent API...")
    yield
    # Shutdown
    print("Shutting down Dream Agent API...")


def create_app() -> FastAPI:
    """Create FastAPI application"""
    app = FastAPI(
        title="Dream Agent API",
        description="K-Beauty 글로벌 트렌드 분석 AI Agent API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: 프로덕션에서는 특정 도메인만 허용
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router, prefix="/health", tags=["health"])
    app.include_router(agent_router, prefix="/api/agent", tags=["agent"])
    app.include_router(websocket_router, tags=["websocket"])

    # Mount static files (CSS, JS)
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Dashboard template
    if TEMPLATES_DIR.exists():
        templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

        @app.get("/", response_class=HTMLResponse, include_in_schema=False)
        async def dashboard(request: Request):
            """Serve HTML Dashboard"""
            return templates.TemplateResponse("index.html", {"request": request})

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.main:app", host="0.0.0.0", port=8000, reload=True)
