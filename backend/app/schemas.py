from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal["admin", "editor", "viewer"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Input):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value):
        return value.strip().lower()


class CreateUser(Input):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    display_name: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=10, max_length=128)
    role: Role = "viewer"

    @field_validator("username", "display_name", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("username")
    @classmethod
    def lowercase_username(cls, value):
        return value.lower()


class UpdateUser(Input):
    role: Role
    active: bool


class ResetPassword(Input):
    password: str = Field(min_length=10, max_length=128)


class ChangePassword(ResetPassword):
    current_password: str = Field(min_length=1, max_length=128)


class CreateDocument(Input):
    name: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1, max_length=10 * 1024 * 1024)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        value = value.strip()
        if not value.lower().endswith((".md", ".txt")) or any(c in value for c in "/\\\x00"):
            raise ValueError("仅支持不含路径的 MD / TXT 文件名")
        return value

    @field_validator("content")
    @classmethod
    def validate_content(cls, value):
        value = value.removeprefix("\ufeff")
        if not value.strip():
            raise ValueError("资料内容为空")
        if len(value.encode("utf-8")) > 10 * 1024 * 1024:
            raise ValueError("资料超过 10 MB 限制")
        return value


class ChatTurn(Input):
    question: str = Field(min_length=1, max_length=500)
    answer: str = Field(max_length=1000)

    @field_validator("question", mode="before")
    @classmethod
    def strip_question(cls, value):
        return value.strip() if isinstance(value, str) else value


class ChatQuestion(Input):
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=5)

    @field_validator("question", mode="before")
    @classmethod
    def strip_question(cls, value):
        return value.strip() if isinstance(value, str) else value
