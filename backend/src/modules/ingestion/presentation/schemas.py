from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel
from pydantic.alias_generators import to_camel


class UploadResponseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    file_id: str
    title: str
    authors: list[str]
    abstract: str
    year: int | None


class ConfirmRequestSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    file_id: str
    title: str
    authors: list[str]
    abstract: str
    year: int | None
    project_id: str


class ConfirmResponseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    document_id: str
    message: str


class AddFromSearchRequestSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    project_id: str
    title: str
    authors: list[str]
    abstract: str
    year: int | None
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    source: Literal["arxiv", "semantic_scholar"]


class AddFromSearchResponseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    document_id: str
    message: str


class SSETicketResponseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    ticket: str


class PaperListItemSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str
    title: str
    authors: list[str]
    year: int | None
    source: str
    status: str
    created_at: datetime
    abstract: str | None = None
    # has_file: chỉ báo có file PDF đã cache (truthy/falsy) — KHÔNG leak server path (Dev Note #5)
    has_file: bool = False
    pdf_url: str | None = None
    url: str | None = None


class PaperListResponseSchema(RootModel[list[PaperListItemSchema]]):
    pass


class DeletePaperResponseSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    message: str


class PatchPaperRequestSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    # Ràng buộc khớp DB (title String(500), year Integer 32-bit) → trả 422 thay vì 500 từ DB.
    title: str | None = Field(default=None, max_length=500)
    authors: list[str] | None = None
    abstract: str | None = None
    year: int | None = Field(default=None, ge=1000, le=2100)


class PatchPaperResponseSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: str
    title: str
    authors: list[str]
    abstract: str | None
    year: int | None
    updated_at: datetime
