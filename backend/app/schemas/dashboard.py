# @TASK PERF-2 - Dashboard unified response schema
# @SPEC Combines companies, clusters, relations, and unread alerts

from pydantic import BaseModel

from app.schemas.alert import AlertResponse
from app.schemas.cluster import ClusterResponse
from app.schemas.company import CompanyResponse
from app.schemas.relation import RelationResponse


class DashboardResponse(BaseModel):
    """Unified response for the main dashboard graph.

    Combines all four data sources that the frontend previously fetched
    independently, reducing API calls from 4 to 1.
    """

    companies: list[CompanyResponse]
    clusters: list[ClusterResponse]
    relations: list[RelationResponse]
    alerts: list[AlertResponse]
