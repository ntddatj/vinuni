import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Project:
    id: str
    user_id: str
    name: str
    description: str | None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def create(user_id: str, name: str, description: str | None = None) -> "Project":
        now = datetime.now(timezone.utc)
        return Project(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            description=description,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
