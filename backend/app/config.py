from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Database
    sentinel_db_url: str = f"sqlite+aiosqlite:///{Path(__file__).parent.parent / 'data' / 'sentinel.db'}"

    # Security
    encryption_key: str = ""  # Fernet key for password encryption

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Scan defaults
    default_sample_size: int = 100
    default_confidence_threshold: float = 0.5

    class Config:
        env_file = ".env"


settings = Settings()
