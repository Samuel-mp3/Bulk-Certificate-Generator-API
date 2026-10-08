import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or defaults.
    """
    DATABASE_URL: str = "sqlite:///./certificates.db"
    CERTIFICATES_DIR: str = "./certificates"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

# Ensure the certificates storage directory exists
os.makedirs(settings.CERTIFICATES_DIR, exist_ok=True)
