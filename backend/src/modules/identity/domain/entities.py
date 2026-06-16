from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class User:
    id: str
    email: str
    hashed_password: str
    role: str
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
