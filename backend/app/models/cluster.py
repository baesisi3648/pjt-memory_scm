# @TASK P0-T0.3 - Database schema: Cluster model
# @SPEC docs/planning/04-database-design.md#clusters

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship


class Cluster(SQLModel, table=True):
    """
    Cluster model representing value chain clusters.

    Examples:
    - 원자재 (Raw Materials)
    - 장비사 (Equipment)
    - 팹 (FAB)
    - 패키징 (Packaging)
    - 모듈 (Module)
    """

    __tablename__ = "clusters"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    name: str = Field(index=True, max_length=255)  # e.g., "원자재", "장비사"
    parent_id: Optional[int] = Field(default=None, foreign_key="clusters.id")
    tier: str = Field(max_length=50)  # raw_material, equipment, fab, packaging, module

    # Relationships
    parent: Optional["Cluster"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Cluster.id"}
    )
    children: list["Cluster"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    companies: list["Company"] = Relationship(back_populates="cluster")
