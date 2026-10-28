import hashlib
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# Argon2id: 19 MiB memory, 2 iterations, one lane.
_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
_dummy_hash = _hasher.hash("dummy-verification-value")

PERMISSIONS = {
    "admin": ["knowledge:read", "knowledge:write", "users:manage"],
    "editor": ["knowledge:read", "knowledge:write"],
    "viewer": ["knowledge:read"],
}


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, encoded: str | None) -> bool:
    try:
        return _hasher.verify(encoded or _dummy_hash, password) and encoded is not None
    except (VerificationError, InvalidHashError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def public_user(row):
    return {
        "id": row["id"], "username": row["username"],
        "display_name": row["display_name"], "role": row["role"],
        "active": bool(row["active"]), "permissions": PERMISSIONS[row["role"]],
    }
