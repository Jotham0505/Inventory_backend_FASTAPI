# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # tell pydantic-settings to load from .env
    model_config = SettingsConfigDict(env_file=".env")

    mongo_uri: str
    db_name: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

settings = Settings()
