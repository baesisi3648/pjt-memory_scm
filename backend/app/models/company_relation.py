# @TASK P0-T0.3 - Database schema: CompanyRelation model
# @SPEC docs/planning/04-database-design.md#company_relations

from typing import Optional

from sqlmodel import SQLModel, Field, Relationship


class CompanyRelation(SQLModel, table=True):
    """
    Company relation model representing supplier-customer relationships.
    """

    __tablename__ = "company_relations"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    source_id: int = Field(foreign_key="companies.id", index=True)
    target_id: int = Field(foreign_key="companies.id", index=True)
    relation_type: str = Field(max_length=50)  # supplier, customer, partner
    strength: Optional[float] = Field(default=None)  # 0-1 scale
    meta_data: Optional[str] = Field(default=None)  # JSON stored as string in SQLite

    # Relationships
    source: "Company" = Relationship(
        back_populates="relations_as_source",
        sa_relationship_kwargs={"foreign_keys": "[CompanyRelation.source_id]"}
    )
    target: "Company" = Relationship(
        back_populates="relations_as_target",
        sa_relationship_kwargs={"foreign_keys": "[CompanyRelation.target_id]"}
    )
