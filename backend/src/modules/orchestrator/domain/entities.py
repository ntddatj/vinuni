from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChatThread:
    id: str
    user_id: str
    project_id: str
    title: str
    created_at: datetime
    updated_at: datetime


@dataclass
class ChatMessage:
    id: str
    thread_id: str
    role: str  # 'user' | 'assistant'
    content: str
    created_at: datetime
