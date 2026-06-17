import logging
import uuid
from pathlib import Path

from backend.src.modules.ingestion.domain.exceptions import FileStorageError
from backend.src.shared.infra.settings import get_settings

logger = logging.getLogger(__name__)


class LocalFileStorage:
    def save(self, file_bytes: bytes, original_filename: str, user_id: str) -> tuple[str, str]:
        """Lưu file vào disk. Trả về (file_id, file_path)."""
        settings = get_settings()
        file_id = str(uuid.uuid4())
        ext = Path(original_filename).suffix.lower()
        target_dir = Path(settings.upload_dir) / user_id
        file_path = str(target_dir / f"{file_id}{ext}")
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            Path(file_path).write_bytes(file_bytes)
        except OSError as e:
            # Thường gặp: thiếu quyền ghi trên volume mount (Errno 13) hoặc hết đĩa (Errno 28).
            logger.error("LocalFileStorage: không ghi được '%s': %s", file_path, e)
            raise FileStorageError(str(e)) from e
        return file_id, file_path
