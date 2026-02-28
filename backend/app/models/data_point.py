# @TASK P0-T0.3 - Database schema: DataPoint model
# @SPEC docs/planning/04-database-design.md#data_points

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship


class DataPoint(SQLModel, table=True):
    """
    Data point model representing collected data metrics.
    """

    __tablename__ = "data_points"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    source_id: int = Field(foreign_key="data_sources.id")
    company_id: Optional[int] = Field(default=None, foreign_key="companies.id", index=True)
    metric: str = Field(max_length=100)  # price, inventory, lead_time, etc.
    value: float = Field()
    unit: Optional[str] = Field(default=None, max_length=50)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Relationships
    source: "DataSource" = Relationship(back_populates="data_points")
    company: Optional["Company"] = Relationship(back_populates="data_points")
