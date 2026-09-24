from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    web_url: str = "http://localhost:5173"
    openai_api_key: str | None = None
    openai_model: str | None = None
    ai_mode: str = "fixture"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
