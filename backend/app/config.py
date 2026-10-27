from dataclasses import dataclass
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    database: Path = ROOT / "data" / "bencao.db"
    cookie_name: str = "bencao_session"
    session_seconds: int = 8 * 60 * 60
    secure_cookie: bool = False
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:3000", "http://localhost:3000",
        "http://127.0.0.1:8000", "http://localhost:8000",
    )

    @classmethod
    def from_env(cls):
        load_dotenv(ROOT / ".env", override=False)
        origins = os.environ.get("ALLOWED_ORIGINS")
        return cls(
            database=Path(os.environ.get("DATABASE_PATH", str(ROOT / "data" / "bencao.db"))),
            secure_cookie=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
            allowed_origins=tuple(x.strip() for x in origins.split(",") if x.strip()) if origins else cls.allowed_origins,
        )
