from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Memory SCM Intelligence Platform"
    VERSION: str = "0.1.0"
    DATABASE_URL: str = "sqlite:///./memory_scm.db"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    NEWS_API_KEY: str = "dd71662f7493444ab5361f1bc8699945"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
