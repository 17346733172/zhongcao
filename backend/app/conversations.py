"""Account-owned append-only history. Reading saved tools never executes them."""

from datetime import timezone
import json
import time
from typing import Literal
from uuid import UUID

from fastapi import Depends, HTTPException
from pydantic import AwareDatetime, ConfigDict, Field, FiniteFloat

from .schemas import Input


class Block(Input):
    type: Literal["paragraph", "heading", "table"]
    text: str = ""
    level: int | None = Field(default=None, ge=1, le=3)
    rows: list[list[str]] = Field(default_factory=list)


class Source(Input):
    # Reference resources also carry provenance metadata outside the render fields.
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    page: int | None = None
    excerpt: str
    fullText: str
    demo: bool
    blocks: list[Block] | None = None
    downloadUrl: str | None = None


class Section(Input):
    title: str
    content: str
    origin: Literal["document", "ai_supplement"] | None = None
    sourceIndex: int | None = None
    sourceIndices: list[int] | None = None


class ToolCall(Input):
    name: str
    title: str
    action: str
    status: Literal["success", "error"] | None = None
    summary: str | None = None
    durationMs: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    fetchedAt: str | None = None
    stale: bool | None = None


class Series(Input):
    name: str
    values: list[FiniteFloat]


class Chart(Input):
    title: str
    unit: str
    categories: list[str]
    series: list[Series]
    source: str | None = None
    fetchedAt: str | None = None
    stale: bool | None = None


class Usage(Input):
    inputTokens: int = Field(ge=0)
    outputTokens: int = Field(ge=0)
    scope: Literal["tool_selection"] | None = None


class Target(Input):
    tab: Literal["overview", "devices", "prescriptions"]
    kind: str | None = None
    status: str | None = None
    deviceId: str | None = None
    alarmStatus: str | None = None
    section: Literal["alarms"] | None = None


class Answer(Input):
    title: str
    introduction: str
    sections: list[Section]
    sources: list[Source]
    mode: Literal["extract", "generated", "no_match", "clarification", "greeting", "data_center"] | None = None
    toolCalls: list[ToolCall] | None = None
    charts: list[Chart] | None = None
    usage: Usage | None = None
    dataCenter: Target | None = None
    resolvedQuestion: str | None = None
    model: str | None = None
    retrievalMethod: Literal["vector"] | None = None
    retrievedSources: list[Source] | None = None


class Message(Input):
    id: UUID
    question: str = Field(min_length=1, max_length=2000)
    time: str = Field(max_length=100)
    answeredAt: AwareDatetime
    answer: Answer
    showSources: bool = Field(strict=True)
    originalAnswer: Answer | None = None


class AppendMessage(Input):
    libraryId: Literal["herbal"]
    message: Message


def register_conversation_routes(app, require):
    database = app.state.database

    @app.get("/api/conversations", tags=["历史会话"])
    def list_conversations(user=Depends(require("knowledge:read"))):
        with database.connect() as db:
            rows = db.execute("""SELECT c.*, COUNT(m.sequence) AS message_count
                FROM conversations c JOIN conversation_messages m
                ON m.user_id = c.user_id AND m.conversation_id = c.id
                WHERE c.user_id = ? GROUP BY c.user_id, c.id
                ORDER BY c.saved_at DESC, c.id""", (user["id"],)).fetchall()
        return [{"id": row["id"], "libraryId": row["library_id"], "title": row["title"],
                 "updatedAt": row["updated_at"], "messageCount": row["message_count"],
                 "messagesLoaded": False, "messages": []} for row in rows]

    @app.get("/api/conversations/{conversation_id}", tags=["历史会话"])
    def read_conversation(conversation_id: UUID, user=Depends(require("knowledge:read"))):
        with database.connect() as db:
            row = db.execute("SELECT * FROM conversations WHERE user_id = ? AND id = ?",
                             (user["id"], str(conversation_id))).fetchone()
            if not row:
                raise HTTPException(404, "会话不存在或不属于当前账号")
            messages = [json.loads(item["content"]) for item in db.execute(
                "SELECT content FROM conversation_messages WHERE user_id = ? AND conversation_id = ? ORDER BY sequence",
                (user["id"], str(conversation_id))).fetchall()]
        return {"id": row["id"], "libraryId": row["library_id"], "title": row["title"],
                "updatedAt": row["updated_at"], "messageCount": len(messages),
                "messagesLoaded": True, "messages": messages}

    @app.post("/api/conversations/{conversation_id}/messages", tags=["历史会话"])
    def append_message(conversation_id: UUID, payload: AppendMessage, user=Depends(require("knowledge:read"))):
        identifier = str(conversation_id)
        message = payload.message.model_dump(mode="json", exclude_none=True, exclude_unset=True)
        content = json.dumps(message, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        with database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("""SELECT content FROM conversation_messages
                WHERE user_id = ? AND conversation_id = ? AND id = ?""",
                (user["id"], identifier, str(payload.message.id))).fetchone()
            if previous:
                if previous["content"] != content:
                    raise HTTPException(409, "同一消息已保存且内容不同，请重新读取会话")
                return {"saved": True, "messageId": str(payload.message.id)}
            timestamp = payload.message.answeredAt.astimezone(timezone.utc).isoformat()
            db.execute("""INSERT INTO conversations(user_id,id,library_id,title,updated_at,saved_at)
                VALUES(?,?,?,?,?,?) ON CONFLICT(user_id,id) DO UPDATE SET
                updated_at=excluded.updated_at, saved_at=excluded.saved_at""",
                (user["id"], identifier, payload.libraryId, payload.message.question[:80], timestamp, time.time()))
            db.execute("INSERT INTO conversation_messages(user_id,conversation_id,id,content) VALUES(?,?,?,?)",
                       (user["id"], identifier, str(payload.message.id), content))
        return {"saved": True, "messageId": str(payload.message.id)}
