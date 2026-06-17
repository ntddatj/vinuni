from pydantic import BaseModel, ConfigDict
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
