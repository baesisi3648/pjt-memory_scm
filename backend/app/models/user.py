# @TASK P0-T0.3 - Database schema: User model
# @SPEC docs/planning/04-database-design.md#users

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship


class User(SQLModel, table=True):
    """
    User model representing platform users.
    """

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    email: str = Field(unique=True, max_length=255)
    hashed_password: str = Field(max_length=255)
    name: Optional[str] = Field(default=None, max_length=255)
    role: str = Field(default="viewer", max_length=50)  # admin, analyst, viewer
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    alert_rules: list["AlertRule"] = Relationship(back_populates="user")
    user_filters: list["UserFilter"] = Relationship(back_populates="user")
