# @TASK P0-T0.3 - Database schema: Alert model
# @SPEC docs/planning/04-database-design.md#alerts

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship


class Alert(SQLModel, table=True):
    """
    Alert model representing supply chain anomalies.
    """

    __tablename__ = "alerts"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    company_id: Optional[int] = Field(default=None, foreign_key="companies.id", index=True)
    severity: str = Field(max_length=20, index=True)  # critical, warning, info
    title: str = Field(max_length=500)
    description: Optional[str] = Field(default=None)
    is_read: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Relationships
    company: Optional["Company"] = Relationship(back_populates="alerts")
