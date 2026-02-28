# @TASK P0-T0.3 - Database schema base configuration
# @SPEC docs/planning/04-database-design.md

from sqlmodel import SQLModel

# All models will inherit from this Base
# SQLModel combines SQLAlchemy and Pydantic for seamless integration
