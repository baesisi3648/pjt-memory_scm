# @TASK P0-T0.3 - Database schema: Company model
# @SPEC docs/planning/04-database-design.md#companies

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship


class Company(SQLModel, table=True):
    """
    Company model representing semiconductor value chain companies.
    """

    __tablename__ = "companies"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    name: str = Field(unique=True, max_length=255, index=True)
    name_kr: Optional[str] = Field(default=None, max_length=255)
    cluster_id: Optional[int] = Field(default=None, foreign_key="clusters.id", index=True)
    tier: Optional[str] = Field(default=None, max_length=50, index=True)
    country: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None)
    meta_data: Optional[str] = Field(default=None, alias="metadata")  # JSON stored as string in SQLite
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    cluster: Optional["Cluster"] = Relationship(back_populates="companies")
    relations_as_source: list["CompanyRelation"] = Relationship(
        back_populates="source",
        sa_relationship_kwargs={"foreign_keys": "CompanyRelation.source_id"}
    )
    relations_as_target: list["CompanyRelation"] = Relationship(
        back_populates="target",
        sa_relationship_kwargs={"foreign_keys": "CompanyRelation.target_id"}
    )
    alerts: list["Alert"] = Relationship(back_populates="company")
    news_items: list["NewsItem"] = Relationship(back_populates="company")
    data_points: list["DataPoint"] = Relationship(back_populates="company")
