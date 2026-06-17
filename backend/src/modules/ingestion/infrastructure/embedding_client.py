import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.shared.infra.llm.router import LLMRouter
from backend.src.shared.infra.settings import get_settings

logger = logging.getLogger(__name__)
EMBEDDING_DIM = 768  # text-embedding-004 output dimension


class GeminiEmbeddingClient:
    """Tạo vector embedding 768 chiều cho child chunks qua Gemini text-embedding-004.

    Lấy API key qua LLMRouter (ưu tiên key của user, fallback system key). Nếu lỗi
    bất kỳ → trả về zero-vectors để worker vẫn hoàn tất (graceful degradation).
    """

    def __init__(self, user_id: str, db: AsyncSession) -> None:
        self._user_id = user_id
        self._db = db

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            api_key = await self._resolve_api_key()
            if not api_key:
                raise RuntimeError("Không có API key Gemini để tạo embedding")

            embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=api_key,
            )
            return await embeddings.aembed_documents(texts)
        except Exception as e:
            logger.warning(
                "GeminiEmbeddingClient: lỗi khi embed batch %d texts: %s — dùng zero-vectors",
                len(texts),
                e,
            )
            return [[0.0] * EMBEDDING_DIM for _ in texts]

    async def _resolve_api_key(self) -> str:
        """Dùng LLMRouter để lấy key của user (đã giải mã) hoặc fallback system key.

        Không nuốt lỗi im lặng: nếu LLMRouter raise (vd key user hỏng giải mã), log lại rồi
        mới fallback system key — để tình huống corrupt-key không biến mất khỏi log và
        degrade âm thầm thành zero-vector.
        """
        try:
            router = LLMRouter(self._db)
            return await router._resolve_api_key(self._user_id)
        except Exception as e:
            logger.warning(
                "Không lấy được API key qua LLMRouter cho user %s (%s) — fallback system key",
                self._user_id,
                e,
            )
            return get_settings().gemini_api_key
