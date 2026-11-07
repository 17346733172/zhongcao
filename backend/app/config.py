from dataclasses import dataclass, field
from urllib.parse import urlsplit
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = ROOT.parent / "code"


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
    decoction_base_url: str = "http://127.0.0.1:8080"
    decoction_api_key: str = field(default="", repr=False)
    decoction_http_username: str = field(default="", repr=False)
    decoction_http_password: str = field(default="", repr=False)
    rag_enabled: bool = True
    rag_data_path: Path = CODE_ROOT / "data"
    rag_persist_dir: Path = CODE_ROOT / "db"
    embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"
    embedding_device: str = "cpu"
    embedding_cpu_storage: str = "bf16"
    rag_warmup: bool = True
    embedding_cache_dir: Path = CODE_ROOT / "models"
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50
    rag_top_k: int = 3
    rag_min_score: float = 0.45
    rag_query_cache_size: int = 128
    rag_answer_cache_size: int = 16
    rag_answer_cache_seconds: int = 120

    def __post_init__(self):
        if not 0 <= self.rag_answer_cache_size <= 128 or not 0 <= self.rag_answer_cache_seconds <= 600:
            raise ValueError("RAG 回答缓存须为 0–128 条，存活时间须为 0–600 秒")
        url = urlsplit(self.deepseek_base_url)
        local_http = url.scheme == "http" and url.hostname in {"127.0.0.1", "localhost", "::1"}
        if (url.scheme != "https" and not local_http) or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("DEEPSEEK_BASE_URL 必须是有效 HTTPS 接口地址，本地测试可使用回环 HTTP")
        decoction = urlsplit(self.decoction_base_url)
        if (decoction.scheme not in {"http", "https"} or not decoction.hostname
                or decoction.username is not None or decoction.password is not None
                or decoction.query or decoction.fragment):
            raise ValueError("DECOCTION_BASE_URL 必须是有效的 HTTP 或 HTTPS 服务地址")
        if bool(self.decoction_http_username) != bool(self.decoction_http_password):
            raise ValueError("仿真平台 HTTP Basic 用户名和密码须同时配置")
        if (self.decoction_http_username and decoction.scheme != "https"
                and decoction.hostname not in {"127.0.0.1", "localhost", "::1"}):
            raise ValueError("仿真平台 HTTP Basic 认证须使用 HTTPS，本地测试可使用回环 HTTP")

    @classmethod
    def from_env(cls):
        load_dotenv(ROOT / ".env", override=False)
        load_dotenv(CODE_ROOT / ".env", override=False)
        if os.environ.get("RAG_ENABLED", "true").lower() != "true":
            raise ValueError("旧关键词 RAG 入口已停用，请使用 RAG_ENABLED=true 的 Qwen + FAISS RAG")
        origins = os.environ.get("ALLOWED_ORIGINS")

        def code_path(key, default):
            value = Path(os.environ.get(key, str(default)))
            return value if value.is_absolute() else (CODE_ROOT / value).resolve()

        return cls(
            database=Path(os.environ.get("DATABASE_PATH", str(ROOT / "data" / "bencao.db"))),
            deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", "").strip(),
            deepseek_base_url=os.environ.get("DEEPSEEK_BASE_URL", cls.deepseek_base_url).strip().rstrip("/"),
            deepseek_model=os.environ.get("DEEPSEEK_MODEL", cls.deepseek_model).strip() or cls.deepseek_model,
            decoction_base_url=os.environ.get("DECOCTION_BASE_URL", cls.decoction_base_url).strip().rstrip("/"),
            decoction_api_key=os.environ.get("DECOCTION_API_KEY", "").strip(),
            decoction_http_username=os.environ.get("DECOCTION_HTTP_USERNAME", "").strip(),
            decoction_http_password=os.environ.get("DECOCTION_HTTP_PASSWORD", ""),
            rag_enabled=os.environ.get("RAG_ENABLED", "true").lower() == "true",
            rag_data_path=code_path("RAG_DATA_PATH", cls.rag_data_path),
            rag_persist_dir=code_path("FAISS_PERSIST_DIR", cls.rag_persist_dir),
            embedding_model=os.environ.get("EMBEDDING_MODEL", cls.embedding_model).strip(),
            embedding_device=os.environ.get("EMBEDDING_DEVICE", cls.embedding_device).strip(),
            embedding_cpu_storage=os.environ.get("EMBEDDING_CPU_STORAGE", cls.embedding_cpu_storage).strip(),
            rag_warmup=os.environ.get("RAG_WARMUP", "true").lower() == "true",
            embedding_cache_dir=code_path("EMBEDDING_CACHE_DIR", cls.embedding_cache_dir),
            rag_chunk_size=int(os.environ.get("RAG_CHUNK_SIZE", cls.rag_chunk_size)),
            rag_chunk_overlap=int(os.environ.get("RAG_CHUNK_OVERLAP", cls.rag_chunk_overlap)),
            rag_top_k=int(os.environ.get("RAG_TOP_K", cls.rag_top_k)),
            rag_min_score=float(os.environ.get("RAG_MIN_SCORE", cls.rag_min_score)),
            rag_query_cache_size=int(os.environ.get("RAG_QUERY_CACHE_SIZE", cls.rag_query_cache_size)),
            rag_answer_cache_size=int(os.environ.get("RAG_ANSWER_CACHE_SIZE", cls.rag_answer_cache_size)),
            rag_answer_cache_seconds=int(os.environ.get("RAG_ANSWER_CACHE_SECONDS", cls.rag_answer_cache_seconds)),
            secure_cookie=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
            allowed_origins=tuple(x.strip() for x in origins.split(",") if x.strip()) if origins else cls.allowed_origins,
        )
