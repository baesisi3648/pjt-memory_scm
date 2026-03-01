from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    PROJECT_NAME: str = "Memory SCM Intelligence Platform"
    VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["dev", "staging", "prod"] = "dev"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./memory_scm.db"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    NEWS_API_KEY: str = ""
    FRED_API_KEY: str = ""
    LOG_LEVEL: str = "INFO"

    @property
    def is_dev(self) -> bool:
        return self.ENVIRONMENT == "dev"

    @property
    def is_prod(self) -> bool:
        return self.ENVIRONMENT == "prod"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
