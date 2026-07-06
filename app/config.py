from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Firebase
    FIREBASE_CREDENTIALS_JSON: str = "{}"
    FIREBASE_WEB_API_KEY: str 

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MAX_TOKENS: int = 600  # global cap per AI call

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    # OneSignal
    ONESIGNAL_APP_ID: str
    ONESIGNAL_API_KEY: str

    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "f99fc443082e4b32c3e13022b970fdac35850e1bbf2fe9818df5ab505daa81ab"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
