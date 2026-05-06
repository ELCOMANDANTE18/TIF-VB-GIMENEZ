from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = Path(__file__).parent.parent  # src/

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BASE_DIR / ".env"),
        env_file_encoding="utf-8",
    )
    FACEBOOK_PAGE_ID: str
    META_APP_ID: str
    META_APP_SECRET: str
    META_VERIFY_TOKEN: str
    PAGE_ACCESS_TOKEN: str
    RISK_THRESHOLD_HIGH: float = 0.7
    RISK_THRESHOLD_MEDIUM: float = 0.4
    URL_WEIGHT: float = 0.6
    TEXT_WEIGHT: float = 0.4

    # Cuenta monitoreada (flia_test)
    FLIA_TEST_IG_USER_ID: str = ""
    FLIA_TEST_TOKEN: str = ""

    # APIs externas (opcionales)
    GROQ_API_KEY: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SLACK_WEBHOOK_URL: str = ""

settings = Settings()