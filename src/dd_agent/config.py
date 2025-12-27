"""Configuration settings for DD Agent."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Azure OpenAI Configuration
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_DEPLOYMENT: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-08-01-preview"

    # API Mode
    USE_AZURE_V1_API: bool = True

    # LLM Settings
    LLM_TEMPERATURE: float = 0.0
    LLM_TIMEOUT_S: float = 60.0

    @property
    def is_configured(self) -> bool:
        """Check if Azure OpenAI is properly configured."""
        return bool(
            self.AZURE_OPENAI_ENDPOINT
            and self.AZURE_OPENAI_API_KEY
            and self.AZURE_OPENAI_DEPLOYMENT
        )


# Global settings instance
settings = Settings()
