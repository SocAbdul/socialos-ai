import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


class TokenCipherConfigurationError(RuntimeError):
    """Raised when token encryption has not been configured safely."""


class TokenCipherError(ValueError):
    """Raised when encrypted credentials cannot be decrypted."""


class FernetTokenCipher:
    def __init__(self, key: str | None) -> None:
        if not key:
            key = "local-development-token-encryption-key"
        normalized = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
        self._fernet = Fernet(normalized)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise TokenCipherError("Encrypted credentials are invalid") from exc
