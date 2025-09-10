from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    llm_provider: str = "mock"
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    model_name: str = "gpt-4o-mini"
    anki_connect_url: str = "http://localhost:8765"
    anki_deck_name: str = "Pharmacy_Recall_AI"
    app_auth_token: str | None = None
    max_upload_bytes: int = 1_048_576

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
