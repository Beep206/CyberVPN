import hashlib
import hmac
import json
from typing import Any


class CryptoBotWebhookHandler:
    def __init__(self, api_token: str) -> None:
        self._secret = hashlib.sha256(api_token.encode()).digest()

    def validate_signature(self, body: bytes, signature: str) -> bool:
        computed = hmac.new(self._secret, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)

    def parse_payload(self, body: bytes) -> dict[str, Any]:
        return json.loads(body)
