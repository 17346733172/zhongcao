from contextlib import asynccontextmanager
import secrets
import sqlite3
import time
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from .config import Settings
from .database import Database
from .chat import ChatService
from .reference_document import download_reference_document, load_reference_document
from .schemas import ChatQuestion, ChangePassword, CreateDocument, CreateUser, Login, ResetPassword, UpdateUser
from .security import PERMISSIONS, hash_password, public_user, token_hash, verify_password


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    database = Database(settings.database)
    chat_service = ChatService(settings)

    @asynccontextmanager
    async def lifespan(app):
        database.initialize()
        yield

    app = FastAPI(title="本草知问 API", version="0.2.0", lifespan=lifespan)
    app.state.database = database
    app.state.settings = settings

    def openapi_schema():
        if app.openapi_schema is None:
            schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
            for operations in schema["paths"].values():
                for method, operation in operations.items():
                    if method in {"post", "put", "patch", "delete"}:
                        operation.setdefault("parameters", []).append({
                            "name": "X-CSRF-Protection", "in": "header", "required": True,
                            "description": "写请求来源保护，填 1。登录后的 Cookie 由浏览器自动发送。",
                            "schema": {"type": "string", "const": "1", "default": "1"},
                        })
            app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = openapi_schema

    @app.middleware("http")
    async def request_boundary(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            if request.headers.get("x-csrf-protection") != "1" or (origin and origin not in settings.allowed_origins):
                return JSONResponse({"detail": "请求来源校验失败，请刷新页面后重试"}, status_code=403)
            # Bound request bytes even for chunked requests before JSON parsing.
            maximum = 12 * 1024 * 1024 if request.url.path == "/api/documents" else (64 * 1024 if request.url.path == "/api/chat" else 16 * 1024)
            size = 0
            chunks = []
            async for chunk in request.stream():
                size += len(chunk)
                if size > maximum:
                    return JSONResponse({"detail": "请求内容超过大小限制"}, status_code=413)
                chunks.append(chunk)
            request._body = b"".join(chunks)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        # Never echo submitted passwords or document content in errors.
        fields = ", ".join(str(item["loc"][-1]) for item in error.errors())
        if request.url.path == "/api/chat":
            return JSONResponse({"detail": "问题需为 1–2000 字；history 最多 5 轮，每轮 question 1–500 字、answer 最多 1000 字，且不接受其他字段。"}, status_code=422)
        return JSONResponse({"detail": f"请检查输入（{fields}）：账号 3–32 位字母、数字或下划线，密码 10–128 位，资料仅支持非空 MD / TXT（10 MB 内）"}, status_code=422)

    def current_user(request: Request):
        token = request.cookies.get(settings.cookie_name)
        if not token or len(token) > 256:
            raise HTTPException(401, "请先登录或重新登录")
        with database.connect() as db:
            row = db.execute("""SELECT u.* FROM users u JOIN sessions s ON s.user_id = u.id
                WHERE s.token_hash = ? AND s.expires_at > ? AND u.active = 1""",
                (token_hash(token), int(time.time()))).fetchone()
        if not row:
            raise HTTPException(401, "登录已失效，请重新登录")
        return row

    def require(permission):
        def authorized(user=Depends(current_user)):
            if permission not in PERMISSIONS[user["role"]]:
                raise HTTPException(403, "当前账号没有此操作权限")
            return user
        return authorized

    def document(row):
        return {
            "id": row["id"], "libraryId": "herbal", "name": row["name"],
            "content": row["content"], "status": "ready", "progress": 100,
            "demo": False, "stored": True,
        }

    @app.get("/api/health")
    def health():
        with database.connect() as db:
            db.execute("SELECT 1")
        return {"status": "ok", "service": "bencao-api"}

    @app.post("/api/auth/login")
    def login(payload: Login, request: Request, response: Response):
        now = int(time.time())
        # Do not trust X-Forwarded-For from clients. User + socket address share a bucket.
        address = request.client.host if request.client else "unknown"
        bucket = token_hash(address + ":" + payload.username)
        with database.connect() as db:
            db.execute("DELETE FROM login_attempts WHERE attempted_at <= ?", (now - 300,))
            count = db.execute("SELECT COUNT(*) FROM login_attempts WHERE bucket = ?", (bucket,)).fetchone()[0]
            if count >= 8:
                raise HTTPException(429, "尝试过于频繁，请 5 分钟后重试", headers={"Retry-After": "300"})
            db.execute("INSERT INTO login_attempts VALUES(?,?)", (bucket, now))
            row = db.execute("SELECT * FROM users WHERE username = ?", (payload.username,)).fetchone()
        if not verify_password(payload.password, row["password_hash"] if row else None) or not row["active"]:
            raise HTTPException(401, "账号或密码错误，或账号已停用")
        token = secrets.token_urlsafe(32)
        with database.connect() as db:
            # Check again inside the write transaction to handle concurrent account changes.
            db.execute("BEGIN IMMEDIATE")
            latest = db.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()
            if not latest["active"] or latest["password_hash"] != row["password_hash"]:
                raise HTTPException(401, "账号信息已变更，请重新登录")
            previous = request.cookies.get(settings.cookie_name)
            if previous:
                db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(previous),))
            db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
            db.execute("DELETE FROM login_attempts WHERE bucket = ?", (bucket,))
            db.execute("INSERT INTO sessions VALUES(?,?,?)", (token_hash(token), row["id"], now + settings.session_seconds))
        response.set_cookie(settings.cookie_name, token, max_age=settings.session_seconds,
                            httponly=True, secure=settings.secure_cookie, samesite="lax", path="/")
        return public_user(latest)

    @app.get("/api/auth/me")
    def me(user=Depends(current_user)):
        return public_user(user)

    @app.post("/api/auth/logout", status_code=204)
    def logout(request: Request, response: Response):
        token = request.cookies.get(settings.cookie_name)
        if token:
            with database.connect() as db:
                db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(token),))
        response.delete_cookie(settings.cookie_name, path="/", httponly=True,
                               secure=settings.secure_cookie, samesite="lax")

    @app.post("/api/auth/password", status_code=204)
    def change_password(payload: ChangePassword, response: Response, user=Depends(current_user)):
        if not verify_password(payload.current_password, user["password_hash"]):
            raise HTTPException(400, "原密码不正确")
        encoded = hash_password(payload.password)
        with database.connect() as db:
            db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (encoded, user["id"]))
            db.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
        response.delete_cookie(settings.cookie_name, path="/", httponly=True,
                               secure=settings.secure_cookie, samesite="lax")

    @app.get("/api/users")
    def list_users(user=Depends(require("users:manage"))):
        with database.connect() as db:
            return [public_user(row) for row in db.execute("SELECT * FROM users ORDER BY id").fetchall()]

    @app.post("/api/users", status_code=201)
    def create_user(payload: CreateUser, user=Depends(require("users:manage"))):
        encoded = hash_password(payload.password)
        with database.connect() as db:
            try:
                cursor = db.execute("INSERT INTO users(username, display_name, password_hash, role, created_at) VALUES(?,?,?,?,?)",
                    (payload.username, payload.display_name, encoded, payload.role, int(time.time())))
            except sqlite3.IntegrityError:
                raise HTTPException(409, "该账号已存在") from None
            return public_user(db.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone())

    @app.patch("/api/users/{user_id}")
    def update_user(user_id: int, payload: UpdateUser, user=Depends(require("users:manage"))):
        if user_id == user["id"]:
            raise HTTPException(400, "不能修改自己的角色或停用当前账号")
        with database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            target = db.execute("SELECT role, active FROM users WHERE id = ?", (user_id,)).fetchone()
            if not target:
                raise HTTPException(404, "账号不存在")
            if target["role"] == "admin" and target["active"] and (payload.role != "admin" or not payload.active):
                if db.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND active = 1").fetchone()[0] <= 1:
                    raise HTTPException(400, "至少保留一个启用的管理员账号")
            db.execute("UPDATE users SET role = ?, active = ? WHERE id = ?", (payload.role, payload.active, user_id))
            db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            return public_user(db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())

    @app.post("/api/users/{user_id}/password", status_code=204)
    def reset_password(user_id: int, payload: ResetPassword, user=Depends(require("users:manage"))):
        if user_id == user["id"]:
            raise HTTPException(400, "请在个人账号页面修改自己的密码")
        encoded = hash_password(payload.password)
        with database.connect() as db:
            if not db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone():
                raise HTTPException(404, "账号不存在")
            db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (encoded, user_id))
            db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    @app.get("/api/ai/status")
    def ai_status(user=Depends(require("knowledge:read"))):
        return {"provider": "DeepSeek", "configured": bool(settings.deepseek_api_key), "model": settings.deepseek_model}

    @app.post("/api/chat")
    def chat(payload: ChatQuestion, user=Depends(require("knowledge:read"))):
        reference = load_reference_document()
        with database.connect() as db:
            documents = [document(row) for row in db.execute("SELECT * FROM documents ORDER BY created_at, id").fetchall()]
        return chat_service.answer(payload.question, documents, reference, [turn.model_dump() for turn in payload.history])

    @app.get("/api/reference-document")
    def reference_document(user=Depends(require("knowledge:read"))):
        return load_reference_document()

    @app.get("/api/reference-document/file")
    def reference_document_file(user=Depends(require("knowledge:read"))):
        return download_reference_document()

    @app.get("/api/documents")
    def list_documents(user=Depends(require("knowledge:read"))):
        with database.connect() as db:
            return [document(row) for row in db.execute("SELECT * FROM documents ORDER BY created_at, id").fetchall()]

    @app.post("/api/documents", status_code=201)
    def create_document(payload: CreateDocument, user=Depends(require("knowledge:write"))):
        identifier = str(uuid4())
        with database.connect() as db:
            db.execute("INSERT INTO documents VALUES(?,?,?,?,?)", (identifier, payload.name, payload.content, user["id"], int(time.time())))
            return document(db.execute("SELECT * FROM documents WHERE id = ?", (identifier,)).fetchone())

    @app.delete("/api/documents/{document_id}", status_code=204)
    def delete_document(document_id: str, user=Depends(require("knowledge:write"))):
        with database.connect() as db:
            if not db.execute("DELETE FROM documents WHERE id = ?", (document_id,)).rowcount:
                raise HTTPException(404, "资料不存在或已移除")

    return app


app = create_app()
