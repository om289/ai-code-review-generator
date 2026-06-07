"""Centralized configuration with validation and environment variable parsing."""

import os
from pathlib import Path


BASE_DIR = Path(__file__).parent.parent


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        self.AI_API_KEY: str = os.getenv("AI_API_KEY", "")
        self.AI_BASE_URL: str = os.getenv(
            "AI_BASE_URL", "https://api.hke-cai.com/inference/v1"
        )
        self.AI_MODEL: str = os.getenv("AI_MODEL", "deepseek/deepseek-v4-pro")

        self.MAX_DIFF_CHARS: int = int(os.getenv("MAX_DIFF_CHARS", "30000"))
        self.REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "60"))
        self.LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
        self.LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))

        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

        self.SECRET_KEY: str = os.getenv("SECRET_KEY", os.urandom(32).hex())
        self.API_KEY: str = os.getenv("APP_API_KEY", "")  # optional API auth

        self.MAX_CONTENT_LENGTH: int = 2 * 1024 * 1024  # 2 MB

        self.SAMPLE_DIFF_PATH: Path = BASE_DIR / "examples" / "sample_diff.patch"
        self.TRAINING_PATH: Path = BASE_DIR / "data" / "train_examples.jsonl"
        self.DB_PATH: Path = BASE_DIR / "storage" / "app.db"

    @property
    def has_api_key(self) -> bool:
        return bool(self.AI_API_KEY and self.AI_API_KEY != "your_api_key_here")

    def validate(self) -> list[str]:
        """Return a list of configuration warnings."""
        warnings: list[str] = []
        if not self.has_api_key:
            warnings.append("AI_API_KEY is not set — LLM features will be unavailable.")
        if self.REQUEST_TIMEOUT < 10:
            warnings.append("REQUEST_TIMEOUT is very low; LLM calls may always timeout.")
        return warnings


def load_dotenv() -> None:
    """Load a local .env file into os.environ (without overwriting existing vars)."""
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


settings = Settings()
