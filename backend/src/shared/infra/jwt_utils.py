from datetime import UTC, datetime, timedelta

import jwt

from backend.src.shared.infra.settings import get_settings

settings = get_settings()


def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(UTC) + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError if invalid.

    Bắt buộc token phải có claim `exp` và `sub`; thiếu một trong hai -> coi như
    token không hợp lệ (MissingRequiredClaimError là lớp con của InvalidTokenError).
    """
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub"]},
    )
