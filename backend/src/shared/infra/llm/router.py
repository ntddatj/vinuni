import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.shared.infra.settings import get_settings

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Định tuyến LLM client với API Key:
    1. Ưu tiên dùng API Key riêng của user (giải mã từ DB)
    2. Fallback về System API Key trong settings nếu user chưa cấu hình
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_llm_client(self, user_id: str, model_name: str = "gemini-2.5-flash"):
        """Trả về ChatGoogleGenerativeAI được cấu hình với API Key phù hợp."""
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = await self._resolve_api_key(user_id)
        return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)

    async def _resolve_api_key(self, user_id: str) -> str:
        from backend.src.modules.identity.infrastructure.credential_repository import PostgresUserCredentialRepository
        from backend.src.modules.identity.infrastructure.encryption import FernetEncryptor

        repo = PostgresUserCredentialRepository(self._db)
        credential = await repo.find_by_user_and_provider(user_id, "gemini")

        if credential:
            try:
                encryptor = FernetEncryptor()
                return encryptor.decrypt(credential.encrypted_api_key)
            except Exception:
                logger.warning("Không thể giải mã API Key của user %s", user_id)
                raise RuntimeError(
                    f"Không thể giải mã API Key Gemini của user {user_id}. "
                    "Key có thể đã bị hỏng hoặc encryption key đã thay đổi."
                )

        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError(
                "Không có API Key Gemini: user chưa cấu hình và GEMINI_API_KEY system chưa được thiết lập"
            )
        return settings.gemini_api_key
