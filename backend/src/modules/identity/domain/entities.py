import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone


@dataclass
class User:
    id: str
    email: str
    hashed_password: str
    role: str
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class UserCredential:
    id: str
    user_id: str
    provider: str
    encrypted_api_key: str
    last_tested_at: datetime | None
    is_valid: bool | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, user_id: str, provider: str, encrypted_api_key: str) -> "UserCredential":
        now = datetime.now(timezone.utc)
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider=provider,
            encrypted_api_key=encrypted_api_key,
            last_tested_at=None,
            is_valid=None,
            created_at=now,
            updated_at=now,
        )
