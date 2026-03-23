"""BillingWatch FastAPI application entry point."""
import os
import time as _time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .routes import webhooks, anomalies, metrics, demo, dashboard, dashboard_ui, beta, onboarding, config, export, tenants, digest


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    print("[BillingWatch] Starting up — all detectors registered.")
    yield
    print("[BillingWatch] Shutting down.")


def create_app() -> FastAPI:
    limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
    app = FastAPI(
        title="BillingWatch",
        description="Real-time Stripe billing anomaly detection",
        version="1.2.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Mount routers
    app.include_router(webhooks.router)
    app.include_router(anomalies.router)
    app.include_router(metrics.router)
    app.include_router(demo.router)
    app.include_router(dashboard.router)
    app.include_router(dashboard_ui.router)
    app.include_router(beta.router)
    app.include_router(onboarding.router)
    app.include_router(config.router)
    app.include_router(export.router)
    app.include_router(tenants.router)
    app.include_router(digest.router)

    _start_time = _time.time()

    @app.get("/health", tags=["system"])
    async def health():
        import sqlite3 as _sqlite3
        import pathlib as _pathlib
        # uptime
        uptime_seconds = int(_time.time() - _start_time)
        # detector count from known list
        detector_count = 10
        # last event from DB
        last_event_at = None
        try:
            _db_path = _pathlib.Path(__file__).parent.parent.parent / "billingwatch.db"
            _conn = _sqlite3.connect(str(_db_path))
            row = _conn.execute("SELECT MAX(received_at) FROM events").fetchone()
            _conn.close()
            if row and row[0] is not None:
                last_event_at = row[0]
        except Exception:
            pass
        return {
            "status": "ok",
            "service": "BillingWatch",
            "version": "1.2.0",
            "uptime_seconds": uptime_seconds,
            "detector_count": detector_count,
            "last_event_at": last_event_at,
        }

    @app.get("/", tags=["system"])
    async def root():
        return {
            "service": "BillingWatch",
            "version": "1.2.0",
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
