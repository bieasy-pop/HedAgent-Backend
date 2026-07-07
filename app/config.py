import os
from pydantic_settings import BaseSettings
from functools import lru_cache


def _get_env_file() -> str:
    env = os.environ.get("APP_ENV", "development")
    return ".env.production" if env == "production" else ".env"


class Settings(BaseSettings):
    DATABASE_URL: str
    FIREBASE_CREDENTIALS_JSON: str = "{}"
    FIREBASE_WEB_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_MAX_TOKENS: int = 600
    GEMINI_API_KEY: str = ""               # NEW — Google AI Studio key
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    ONESIGNAL_APP_ID: str = ""
    ONESIGNAL_API_KEY: str = ""
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me"

    class Config:
        env_file = _get_env_file()
        extra = "ignore"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
