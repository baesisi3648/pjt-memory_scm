import logging
import time
from datetime import datetime

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlmodel import Session, text

from app.api import (
    alert_rules_router,
    alerts_router,
    auth_router,
    clusters_router,
    companies_router,
    company_relations_router,
    exchange_router,
    filters_router,
    news_router,
    relations_router,
    stock_router,
)
from app.core.config import settings
from app.core.database import get_session
from app.core.logging_config import setup_logging
from app.core.rate_limit import limiter

# Configure structured logging before anything else runs.
setup_logging()

logger = logging.getLogger(__name__)

# Store application start time for uptime calculation
APP_START_TIME = datetime.now()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
)

# Rate-limiting: attach limiter to app state so slowapi can find it,
# register the SlowAPI middleware, and map RateLimitExceeded → 429.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log method, path, status code and wall-clock duration for every request."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "method=%s path=%s status=%d duration_ms=%.1f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(companies_router, prefix="/api/v1/companies", tags=["companies"])
app.include_router(clusters_router, prefix="/api/v1/clusters", tags=["clusters"])
app.include_router(relations_router, prefix="/api/v1/relations", tags=["relations"])
# Company-specific relations: GET /api/v1/companies/{id}/relations
app.include_router(company_relations_router, prefix="/api/v1/companies", tags=["relations"])
# Alerts: GET /api/v1/alerts, PATCH /api/v1/alerts/{id}/read,
#          GET /api/v1/companies/{company_id}/alerts
app.include_router(alerts_router, prefix="/api/v1", tags=["alerts"])
# News: GET /api/v1/companies/{company_id}/news
app.include_router(news_router, prefix="/api/v1", tags=["news"])
# User Filters: GET/POST/DELETE /api/v1/filters
app.include_router(filters_router, prefix="/api/v1/filters", tags=["filters"])
# Alert Rules: GET/POST/PUT/PATCH/DELETE /api/v1/alert-rules
app.include_router(alert_rules_router, prefix="/api/v1/alert-rules", tags=["alert-rules"])
# Stock: GET /api/v1/companies/{company_id}/stock
app.include_router(stock_router, prefix="/api/v1/companies", tags=["stock"])
# Exchange rates: GET /api/v1/exchange-rates
app.include_router(exchange_router, prefix="/api/v1", tags=["exchange"])


async def check_database(session: Session = Depends(get_session)) -> str:
    """Check database connectivity by executing a simple query."""
    try:
        session.exec(text("SELECT 1"))
        return "ok"
    except Exception as e:
        logger.error("Database health check failed: %s", str(e))
        return "error"


@app.get("/api/v1/health")
async def health_check(db_status: str = Depends(check_database)):
    """
    Enhanced health check endpoint.

    Returns:
        - status: "ok" if healthy, "error" if not
        - uptime_seconds: Seconds since application started
        - database: "ok" or "error"
        - version: Application version from settings
    """
    uptime_seconds = int((datetime.now() - APP_START_TIME).total_seconds())

    return {
        "status": "ok",
        "uptime_seconds": uptime_seconds,
        "database": db_status,
        "version": settings.VERSION,
    }
