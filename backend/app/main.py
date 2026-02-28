from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    alert_rules_router,
    alerts_router,
    auth_router,
    clusters_router,
    companies_router,
    company_relations_router,
    filters_router,
    news_router,
    relations_router,
    stock_router,
)
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "version": settings.VERSION}
