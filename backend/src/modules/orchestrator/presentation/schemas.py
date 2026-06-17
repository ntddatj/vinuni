from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

_DEFAULT_TITLE = "Cuộc trò chuyện mới"


class CreateThreadRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    project_id: UUID
    title: str = Field(default=_DEFAULT_TITLE, max_length=500)

    @field_validator("title")
    @classmethod
    def _normalize_title(cls, v: str) -> str:
        v = v.strip()
        return v or _DEFAULT_TITLE


class ChatThreadResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: str
    user_id: str
    project_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    id: str
    thread_id: str
    role: str
    content: str
    created_at: datetime


class InvokeRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    thread_id: UUID
    message: str = Field(..., min_length=1, max_length=4000)


class InvokeResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    answer: str
    thread_id: str


class SendMessageRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    message: str = Field(..., min_length=1, max_length=4000)


class SendMessageResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    run_id: str


class GetSuggestionsRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    active_tab: str = Field(..., description="Tab đang active: library | graph | writing")
    document_count: int = Field(..., ge=0)
    has_draft: bool = False


class SuggestionItemResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    label: str
    action_key: str


class CitationDetailResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    title: str
    text: str
