import logging

from cryptography.fernet import Fernet

from backend.src.shared.infra.settings import get_settings

logger = logging.getLogger(__name__)


class FernetEncryptor:
    def __init__(self) -> None:
        settings = get_settings()
        key = settings.fernet_secret_key
        if not key:
            logger.warning("FERNET_SECRET_KEY chưa được cấu hình. Dùng ephemeral key cho dev/test.")
            key = Fernet.generate_key().decode()
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()

    @staticmethod
    def mask(plaintext: str) -> str:
        if len(plaintext) <= 4:
            return "••••"
        return "••••••••" + plaintext[-4:]
