# @TASK P0-T0.3 - Database schema: AlertRule model
# @SPEC docs/planning/04-database-design.md#alert_rules

from typing import Optional

from sqlmodel import SQLModel, Field, Relationship


class AlertRule(SQLModel, table=True):
    """
    Alert rule model representing user-configured alert rules.
    """

    __tablename__ = "alert_rules"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    user_id: int = Field(foreign_key="users.id")
    name: str = Field(max_length=255)
    condition: str = Field()  # JSON stored as string in SQLite
    is_active: bool = Field(default=True)

    # Relationships
    user: "User" = Relationship(back_populates="alert_rules")
