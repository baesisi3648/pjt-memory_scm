# @TASK P1-R1-T1 - API router initialization
# @TASK P2-R1-T1, P2-R2-T1, P2-R3-T1 - Resource API routers
# @TASK P2-R4-T1 - Alerts resource router
# @TASK P2-R5-T1 - News resource router
# @TASK P2-R6-T1 - User Filters resource router
# @TASK P2-R7-T1 - Alert Rules resource router

from app.api.auth import router as auth_router
from app.api.clusters import router as clusters_router
from app.api.companies import router as companies_router
from app.api.relations import company_relations_router, router as relations_router
from app.api.alerts import router as alerts_router
from app.api.news import router as news_router
from app.api.filters import router as filters_router
from app.api.alert_rules import router as alert_rules_router

__all__ = [
    "auth_router",
    "companies_router",
    "clusters_router",
    "relations_router",
    "company_relations_router",
    "alerts_router",
    "news_router",
    "filters_router",
    "alert_rules_router",
]
