from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pydantic.alias_generators import to_camel

# bcrypt từ chối mật khẩu dài quá 72 byte (raise ValueError). Chặn sớm ở tầng
# validation để trả 422 rõ ràng thay vì để bcrypt làm vỡ thành HTTP 500.
_BCRYPT_MAX_BYTES = 72


class RegisterRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def _password_within_bcrypt_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > _BCRYPT_MAX_BYTES:
            raise ValueError(f"Mật khẩu không được vượt quá {_BCRYPT_MAX_BYTES} byte")
        return value


class LoginRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    # Login KHÔNG áp lại policy độ dài của lúc tạo tài khoản: chỉ cần khác rỗng.
    # Mọi credential sai (kể cả quá ngắn/quá dài) đều quy về 401 generic ở use case.
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    id: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SaveApiKeyRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    api_key: str = Field(alias="apiKey", min_length=1, max_length=512)

    @field_validator("api_key", mode="before")
    @classmethod
    def strip_api_key(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v
