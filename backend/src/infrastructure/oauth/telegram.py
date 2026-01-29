import hmac
import hashlib
from typing import Dict, Optional
from src.config.settings import settings

class TelegramOAuthProvider:
    """Telegram OAuth authentication provider"""

    def __init__(self):
        self.bot_token = settings.telegram_bot_token
        self.bot_username = settings.telegram_bot_username

    def authorize_url(self, redirect_uri: str) -> str:
        """
        Generate Telegram OAuth authorization URL

        Args:
            redirect_uri: URL to redirect after authentication

        Returns:
            Telegram auth URL
        """
        base_url = "https://oauth.telegram.org/auth"
        params = f"bot_id={self.bot_username}&origin={redirect_uri}&request_access=write"
        return f"{base_url}?{params}"

    async def exchange_code(self, auth_data: Dict[str, str]) -> Optional[Dict]:
        """
        Verify Telegram auth data and extract user information

        Args:
            auth_data: Dictionary containing Telegram auth data (id, first_name, hash, etc.)

        Returns:
            User info dict if valid, None otherwise
        """
        if not self._verify_telegram_auth(auth_data):
            return None

        return {
            "id": auth_data.get("id"),
            "username": auth_data.get("username"),
            "first_name": auth_data.get("first_name"),
            "last_name": auth_data.get("last_name"),
            "photo_url": auth_data.get("photo_url")
        }

    def _verify_telegram_auth(self, auth_data: Dict[str, str]) -> bool:
        """
        Verify Telegram authentication data using HMAC-SHA256

        Args:
            auth_data: Dictionary containing Telegram auth data

        Returns:
            True if data is valid, False otherwise
        """
        check_hash = auth_data.get("hash")
        if not check_hash:
            return False

        # Create a copy without the hash
        data_check = {k: v for k, v in auth_data.items() if k != "hash"}

        # Create data check string
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data_check.items()))

        # Calculate secret key
        secret_key = hashlib.sha256(self.bot_token.encode()).digest()

        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        return calculated_hash == check_hash
