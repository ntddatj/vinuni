from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, RootModel
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


class PaperListResponseSchema(RootModel[list[PaperListItemSchema]]):
    pass
