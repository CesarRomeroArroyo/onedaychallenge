from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    web_url: str = "http://localhost:7988"
    web_origins: str = "http://localhost:7988,http://127.0.0.1:7988"
    openai_api_key: str | None = None
    openai_model: str | None = None
    ai_mode: str = "fixture"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


def cors_origins() -> list[str]:
    return [origin.strip() for origin in settings.web_origins.split(",") if origin.strip()]
