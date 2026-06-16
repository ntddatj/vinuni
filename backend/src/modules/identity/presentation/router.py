from fastapi import APIRouter, Depends, HTTPException

from backend.src.modules.identity.application.dtos import RegisterUserDTO
from backend.src.modules.identity.application.use_cases import RegisterUserUseCase
from backend.src.modules.identity.domain.exceptions import EmailAlreadyExistsError
from backend.src.modules.identity.domain.repositories import UserRepository
from backend.src.modules.identity.infrastructure.dependencies import get_user_repository
from backend.src.modules.identity.presentation.schemas import RegisterRequest, UserResponse

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
