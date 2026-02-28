# @TASK P0-T0.3 - Database schema: UserFilter model
# @SPEC docs/planning/04-database-design.md#user_filters

from typing import Optional

from sqlmodel import SQLModel, Field, Relationship


class UserFilter(SQLModel, table=True):
    """
    User filter model representing saved filter presets.
    """

    __tablename__ = "user_filters"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    user_id: int = Field(foreign_key="users.id")
    name: str = Field(max_length=255)
    company_ids: str = Field()  # JSON array stored as string in SQLite
    is_default: bool = Field(default=False)

    # Relationships
    user: "User" = Relationship(back_populates="user_filters")
