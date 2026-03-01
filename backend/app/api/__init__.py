# @TASK P1-R1-T1 - API router initialization
# @TASK P2-R1-T1, P2-R2-T1, P2-R3-T1 - Resource API routers
# @TASK P2-R4-T1 - Alerts resource router
# @TASK P2-R5-T1 - News resource router
# @TASK P2-R6-T1 - User Filters resource router
# @TASK P2-R7-T1 - Alert Rules resource router
# @TASK RISK-1 - Risk score calculation router
# @TASK PERF-2 - Dashboard unified endpoint router
# @TASK HHI-T1 - Concentration index (HHI) router
# @TASK GDELT-2 - GDELT geopolitical events router

from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.clusters import router as clusters_router
from app.api.companies import router as companies_router
from app.api.relations import company_relations_router, router as relations_router
from app.api.alerts import router as alerts_router
from app.api.news import router as news_router
from app.api.filters import router as filters_router
from app.api.alert_rules import router as alert_rules_router
from app.api.stock import router as stock_router
from app.api.data_points import router as data_points_router
from app.api.exchange import router as exchange_router
from app.api.rss import router as rss_router
from app.api.fred import router as fred_router
from app.api.risk import router as risk_router
from app.api.concentration import router as concentration_router
from app.api.sentiment import router as sentiment_router
from app.api.trends import router as trends_router
from app.api.gdelt import router as gdelt_router
from app.api.ws import router as ws_router

__all__ = [
    "auth_router",
    "companies_router",
    "clusters_router",
    "relations_router",
    "company_relations_router",
    "alerts_router",
    "data_points_router",
    "news_router",
    "filters_router",
    "alert_rules_router",
    "stock_router",
    "exchange_router",
    "rss_router",
    "fred_router",
    "dashboard_router",
    "risk_router",
    "concentration_router",
    "sentiment_router",
    "trends_router",
    "gdelt_router",
    "ws_router",
]
