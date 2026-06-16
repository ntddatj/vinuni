from fastapi import APIRouter, Depends, HTTPException, Response

from backend.src.modules.identity.application.dtos import LoginUserDTO, RegisterUserDTO
from backend.src.modules.identity.application.use_cases import (
    DeleteApiKeyUseCase,
    ListApiKeysUseCase,
    LoginUserUseCase,
    RegisterUserUseCase,
    SaveApiKeyUseCase,
    TestApiKeyUseCase,
)
from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.domain.exceptions import (
    CredentialNotFoundError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
)
from backend.src.modules.identity.domain.repositories import UserCredentialRepository, UserRepository
from backend.src.modules.identity.infrastructure.auth_dependencies import get_current_user
from backend.src.modules.identity.infrastructure.dependencies import get_credential_repository, get_user_repository
from backend.src.modules.identity.infrastructure.encryption import FernetEncryptor
from backend.src.modules.identity.presentation.schemas import LoginRequest, RegisterRequest, SaveApiKeyRequest, UserResponse
from backend.src.shared.infra.settings import get_settings

settings = get_settings()
router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=UserResponse, status_code=201)
async def register(
    request: RegisterRequest,
    repo: UserRepository = Depends(get_user_repository),
) -> UserResponse:
    """Đăng ký tài khoản mới. Tài khoản đầu tiên nhận quyền Admin."""
    try:
        use_case = RegisterUserUseCase(repo)
        result = await use_case.execute(
            RegisterUserDTO(email=request.email, password=request.password)
        )
        return UserResponse.model_validate(result, from_attributes=True)
    except EmailAlreadyExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/login", response_model=UserResponse)
async def login(
    request: LoginRequest,
    response: Response,
    repo: UserRepository = Depends(get_user_repository),
) -> UserResponse:
    """Đăng nhập và nhận JWT qua HttpOnly cookie."""
    try:
        use_case = LoginUserUseCase(repo)
        result = await use_case.execute(
            LoginUserDTO(email=request.email, password=request.password)
        )
        response.set_cookie(
            key="access_token",
            value=result.access_token,
            httponly=True,
            samesite="lax",
            max_age=settings.jwt_expire_hours * 3600,
            path="/",
        )
        return UserResponse.model_validate(result, from_attributes=True)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Lấy thông tin người dùng hiện tại."""
    return UserResponse.model_validate(current_user, from_attributes=True)


@router.post("/auth/logout")
async def logout(response: Response) -> dict:
    """Đăng xuất và xóa cookie."""
    response.delete_cookie(key="access_token", path="/")
    return {"message": "Đã đăng xuất thành công"}


@router.get("/user/api-keys")
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    repo: UserCredentialRepository = Depends(get_credential_repository),
) -> list[dict]:
    """Lấy danh sách API Keys (masked) của user hiện tại."""
    encryptor = FernetEncryptor()
    use_case = ListApiKeysUseCase(repo, encryptor)
    return await use_case.execute(current_user.id)


@router.put("/user/api-keys/{provider}", status_code=200)
async def save_api_key(
    provider: str,
    request: SaveApiKeyRequest,
    current_user: User = Depends(get_current_user),
    repo: UserCredentialRepository = Depends(get_credential_repository),
) -> dict:
    """Lưu hoặc cập nhật API Key cho provider."""
    if provider not in {"gemini"}:
        raise HTTPException(status_code=400, detail=f"Provider không hợp lệ: {provider}")
    encryptor = FernetEncryptor()
    use_case = SaveApiKeyUseCase(repo, encryptor)
    await use_case.execute(current_user.id, provider, request.api_key)
    return {"message": "API Key đã được lưu thành công"}


@router.delete("/user/api-keys/{provider}", status_code=204)
async def delete_api_key(
    provider: str,
    current_user: User = Depends(get_current_user),
    repo: UserCredentialRepository = Depends(get_credential_repository),
) -> None:
    """Xóa API Key cho provider."""
    if provider not in {"gemini"}:
        raise HTTPException(status_code=400, detail=f"Provider không hợp lệ: {provider}")
    use_case = DeleteApiKeyUseCase(repo)
    await use_case.execute(current_user.id, provider)


@router.post("/user/api-keys/{provider}/test")
async def test_api_key(
    provider: str,
    current_user: User = Depends(get_current_user),
    repo: UserCredentialRepository = Depends(get_credential_repository),
) -> dict:
    """Test kết nối API Key cho provider."""
    if provider not in {"gemini"}:
        raise HTTPException(status_code=400, detail=f"Provider không hợp lệ: {provider}")
    encryptor = FernetEncryptor()
    use_case = TestApiKeyUseCase(repo, encryptor)
    try:
        return await use_case.execute(current_user.id, provider)
    except CredentialNotFoundError:
        raise HTTPException(status_code=404, detail=f"Chưa cấu hình API Key cho {provider}")
