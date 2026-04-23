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


settings = Settings()
