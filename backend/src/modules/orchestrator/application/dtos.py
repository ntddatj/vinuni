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
