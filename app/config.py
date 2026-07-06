import os
from pydantic_settings import BaseSettings
from functools import lru_cache


def _get_env_file() -> str:
    """
    Automatically picks the correct .env file based on APP_ENV.
    - development (default) → .env
    - production            → .env.production
    This means locally you always hit the dev Firebase project,
    and Render always hits the prod Firebase project.
    """
    env = os.environ.get("APP_ENV", "development")
    if env == "production":
        return ".env.production"
    return ".env"


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Firebase
    FIREBASE_CREDENTIALS_JSON: str = "{}"
    FIREBASE_WEB_API_KEY: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MAX_TOKENS: int = 600

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # OneSignal
    ONESIGNAL_APP_ID: str = ""
    ONESIGNAL_API_KEY: str = ""

    # App
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
