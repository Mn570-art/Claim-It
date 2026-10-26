"""Environment configuration. API keys stay in the environment, never in the database."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


def _abs(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (BACKEND_ROOT / candidate).resolve()
    return candidate


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    sarvam_api_key: str = ""
    max_upload_mb: int = 10
    max_pdf_pages: int = 20
    database_url: str = "sqlite:///./data/claimit.db"
    upload_dir: str = "./data/uploads"
    sample_dir: str = "../sample_data"
    cors_origins: str = "http://127.0.0.1:43123,http://localhost:43123"
    sarvam_timeout_seconds: int = 60
    doc_job_timeout_seconds: int = 180
    retention_days: int = 30

    @property
    def sarvam_configured(self) -> bool:
        return bool(self.sarvam_api_key.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def upload_path(self) -> Path:
        return _abs(self.upload_dir)

    @property
    def sample_path(self) -> Path:
        return _abs(self.sample_dir)

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        prefix = "sqlite:///./"
        if url.startswith(prefix):
            relative = url[len(prefix) :]
            return "sqlite:///" + str(_abs(relative))
        if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
            # sqlite:///relative or sqlite:///absolute-without-extra-slash handled above
            rest = url[len("sqlite:///") :]
            if not rest.startswith("/"):
                return "sqlite:///" + str(_abs(rest))
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
