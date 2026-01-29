import hashlib
import hmac


class RemnawaveWebhookValidator:
    def __init__(self, secret: str) -> None:
        self._secret = secret.encode()

    def validate_signature(self, body: bytes, signature: str) -> bool:
        computed = hmac.new(self._secret, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)
