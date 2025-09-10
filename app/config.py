from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    llm_provider: str = "mock"  # "gemini" or "mock"
    gemini_api_key: str | None = None
    model_name: str = "gemini-1.5-flash"
    anki_connect_url: str = "http://localhost:8765"
    anki_deck_name: str = "Pharmacy_Recall_AI"
    app_auth_token: str | None = None
    max_upload_bytes: int = 1_048_576

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
