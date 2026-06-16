from dataclasses import dataclass
from datetime import datetime


@dataclass
class RegisterUserDTO:
    email: str
    password: str


@dataclass
class UserResponseDTO:
    id: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class LoginUserDTO:
    email: str
    password: str


@dataclass
class LoginResponseDTO:
    id: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    access_token: str


@dataclass
class SaveApiKeyDTO:
    user_id: str
    provider: str
    plain_api_key: str


@dataclass
class TestApiKeyDTO:
    user_id: str
    provider: str
