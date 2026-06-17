from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class SystemSettingSchema(BaseModel):
    key: str
    value: str
    description: str | None
    updated_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class UpdateSettingRequest(BaseModel):
    value: str


class PublicSettingsSchema(BaseModel):
    """Cấu hình công khai (không nhạy cảm) cho client thường — không cần quyền admin."""

    max_papers_per_project: int

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
