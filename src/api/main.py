"""BillingWatch FastAPI application entry point."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import webhooks, anomalies, metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    print("[BillingWatch] Starting up — all detectors registered.")
    yield
    print("[BillingWatch] Shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="BillingWatch",
        description="Real-time Stripe billing anomaly detection",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    app.include_router(webhooks.router)
    app.include_router(anomalies.router)
    app.include_router(metrics.router)

    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "service": "BillingWatch"}

    @app.get("/", tags=["system"])
    async def root():
        return {
            "service": "BillingWatch",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()

# Add static file serving for landing page
import pathlib
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_LANDING = pathlib.Path(__file__).parent.parent.parent / 'landing'

def _add_static(app: FastAPI):
    if _LANDING.exists():
        app.mount('/landing', StaticFiles(directory=str(_LANDING), html=True), name='landing')

        @app.get('/', include_in_schema=False)
        async def root():
            return FileResponse(str(_LANDING / 'index.html'))


_add_static(app)
