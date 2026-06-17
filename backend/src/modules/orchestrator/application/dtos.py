from dataclasses import dataclass


@dataclass
class CreateThreadDTO:
    user_id: str
    project_id: str
    title: str = "Cuộc trò chuyện mới"


@dataclass
class GetThreadMessagesDTO:
    thread_id: str
    requesting_user_id: str


@dataclass
class ListThreadsDTO:
    user_id: str
    project_id: str


@dataclass
class InvokeDTO:
    thread_id: str
    message: str
    user_id: str


@dataclass
class SendMessageDTO:
    thread_id: str
    message: str
    user_id: str


@dataclass
class StreamDTO:
    run_id: str


@dataclass
class GetSuggestionsDTO:
    active_tab: str  # 'library' | 'graph' | 'writing'
    document_count: int
    has_draft: bool


@dataclass
class GetCitationDetailDTO:
    chunk_id: str  # UUID của ChildChunkORM
    user_id: str  # owner scoping — chỉ trả chunk thuộc paper của chính user (chống IDOR)
