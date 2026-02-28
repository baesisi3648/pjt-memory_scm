# @TASK P0-T0.3 - Database schema: DataSource model
# @SPEC docs/planning/04-database-design.md#data_sources

from typing import Optional

from sqlmodel import SQLModel, Field, Relationship


class DataSource(SQLModel, table=True):
    """
    Data source model representing data collection sources.
    """

    __tablename__ = "data_sources"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    name: str = Field(max_length=255)
    type: str = Field(max_length=50)  # api, crawl, manual
    config: Optional[str] = Field(default=None)  # JSON stored as string in SQLite
    is_active: bool = Field(default=True)

    # Relationships
    data_points: list["DataPoint"] = Relationship(back_populates="source")
