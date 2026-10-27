from dataclasses import dataclass, field
from urllib.parse import urlsplit
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

    deepseek_api_key: str = field(default="", repr=False)
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"

    def __post_init__(self):
        url = urlsplit(self.deepseek_base_url)
        local_http = url.scheme == "http" and url.hostname in {"127.0.0.1", "localhost", "::1"}
        if (url.scheme != "https" and not local_http) or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("DEEPSEEK_BASE_URL 必须是有效 HTTPS 接口地址，本地测试可使用回环 HTTP")

    @classmethod
    def from_env(cls):
        load_dotenv(ROOT / ".env", override=False)
        origins = os.environ.get("ALLOWED_ORIGINS")
        return cls(
            database=Path(os.environ.get("DATABASE_PATH", str(ROOT / "data" / "bencao.db"))),
            deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", "").strip(),
            deepseek_base_url=os.environ.get("DEEPSEEK_BASE_URL", cls.deepseek_base_url).strip().rstrip("/"),
            deepseek_model=os.environ.get("DEEPSEEK_MODEL", cls.deepseek_model).strip() or cls.deepseek_model,
            secure_cookie=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
            allowed_origins=tuple(x.strip() for x in origins.split(",") if x.strip()) if origins else cls.allowed_origins,
        )
