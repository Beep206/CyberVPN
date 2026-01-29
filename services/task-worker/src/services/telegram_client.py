"""Telegram Bot API client for CyberVPN task-worker microservice.

Provides a production-ready async client for sending notifications and alerts
to Telegram users and administrators via the Telegram Bot API.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)


class TelegramAPIError(Exception):
    """Custom exception for Telegram API errors."""

    pass


class TelegramClient:
    """Async HTTP client for Telegram Bot API with rate limiting and error handling.

    Wraps httpx.AsyncClient with Telegram-specific logic including:
    - Automatic rate limiting (25 requests/sec to stay below Telegram's 30/sec limit)
    - Smart retry logic for 429 Too Many Requests errors
    - Error categorization and handling
    - Admin alert broadcasting with severity emojis
    - Context manager support for proper resource cleanup
    """

    # Severity emoji mapping for admin alerts
    SEVERITY_EMOJIS = {
        "info": "ℹ️",
        "warning": "⚠️",
        "critical": "🚨",
        "resolved": "✅",
    }

    def __init__(self) -> None:
        """Initialize the Telegram client with settings and rate limiting."""
        self._settings = get_settings()
        self._base_url = f"https://api.telegram.org/bot{self._settings.telegram_bot_token.get_secret_value()}"
        self._timeout = httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0)
        self._rate_limiter = asyncio.Semaphore(25)  # Stay below Telegram's 30 req/sec limit
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "TelegramClient":
        """Context manager entry: initialize the HTTP client."""
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout)
        logger.info("telegram_client_initialized", base_url=self._base_url)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit: close the HTTP client."""
        if self._client:
            await self._client.aclose()
            logger.info("telegram_client_closed")

    def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure the HTTP client is initialized."""
        if not self._client:
            raise RuntimeError("TelegramClient must be used as a context manager (async with TelegramClient())")
        return self._client

    async def _make_request(self, method: str, endpoint: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a rate-limited request to the Telegram API with automatic retry on 429.

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint (e.g., "sendMessage")
            json_data: JSON payload for POST requests

        Returns:
            Telegram API response data

        Raises:
            TelegramAPIError: On API errors (400, 403, etc.)
        """
        client = self._ensure_client()

        async with self._rate_limiter:
            try:
                response = await client.request(method, endpoint, json=json_data)
                response.raise_for_status()
                result = response.json()

                if not result.get("ok"):
                    error_description = result.get("description", "Unknown error")
                    logger.error(
                        "telegram_api_error",
                        endpoint=endpoint,
                        error_code=result.get("error_code"),
                        description=error_description,
                    )
                    raise TelegramAPIError(f"Telegram API error: {error_description}")

                return result.get("result", {})

            except httpx.HTTPStatusError as e:
                # Handle 429 Too Many Requests with retry
                if e.response.status_code == 429:
                    retry_after = e.response.json().get("parameters", {}).get("retry_after", 1)
                    logger.warning(
                        "telegram_rate_limit_hit",
                        endpoint=endpoint,
                        retry_after=retry_after,
                    )
                    await asyncio.sleep(retry_after)

                    # Retry once
                    try:
                        response = await client.request(method, endpoint, json=json_data)
                        response.raise_for_status()
                        result = response.json()
                        if result.get("ok"):
                            return result.get("result", {})
                    except Exception as retry_error:
                        logger.error("telegram_retry_failed", endpoint=endpoint, error=str(retry_error))
                        raise TelegramAPIError(f"Telegram API retry failed: {retry_error}") from retry_error

                # Handle 400 Bad Request
                elif e.response.status_code == 400:
                    error_msg = e.response.json().get("description", "Bad Request")
                    logger.error("telegram_bad_request", endpoint=endpoint, error=error_msg)
                    raise TelegramAPIError(f"Bad Request: {error_msg}") from e

                # Handle 403 Forbidden (user blocked bot)
                elif e.response.status_code == 403:
                    logger.warning(
                        "telegram_forbidden",
                        endpoint=endpoint,
                        chat_id=json_data.get("chat_id") if json_data else None,
                        message="User may have blocked the bot",
                    )
                    raise TelegramAPIError("Forbidden: user blocked the bot or bot was kicked") from e

                # Handle other HTTP errors
                else:
                    logger.error("telegram_http_error", endpoint=endpoint, status_code=e.response.status_code)
                    raise TelegramAPIError(f"HTTP {e.response.status_code}: {e.response.text}") from e

            except httpx.RequestError as e:
                logger.error("telegram_request_error", endpoint=endpoint, error=str(e))
                raise TelegramAPIError(f"Request error: {e}") from e

    async def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML") -> dict[str, Any]:
        """Send a message to a Telegram chat.

        Args:
            chat_id: Telegram chat ID
            text: Message text (supports HTML or Markdown based on parse_mode)
            parse_mode: Parse mode for formatting (default: HTML)

        Returns:
            Dictionary with message_id and sent_at timestamp

        Raises:
            TelegramAPIError: On API errors
        """
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        logger.info("sending_telegram_message", chat_id=chat_id, text_length=len(text))

        result = await self._make_request("POST", "sendMessage", payload)
        message_id = result.get("message_id")
        sent_at = datetime.now(UTC).isoformat()

        logger.info("telegram_message_sent", chat_id=chat_id, message_id=message_id, sent_at=sent_at)

        return {
            "message_id": message_id,
            "sent_at": sent_at,
        }

    async def send_admin_alert(self, text: str, severity: str = "info") -> list[dict[str, Any]]:
        """Send an alert to all configured admin Telegram IDs.

        Args:
            text: Alert message text
            severity: Alert severity level (info, warning, critical, resolved)

        Returns:
            List of dictionaries with message_id and sent_at for each admin

        Raises:
            TelegramAPIError: On critical failures (logged and re-raised)
        """
        emoji = self.SEVERITY_EMOJIS.get(severity, self.SEVERITY_EMOJIS["info"])
        formatted_text = f"{emoji} <b>{severity.upper()}</b>\n\n{text}"

        admin_ids = self._settings.admin_telegram_ids
        if not admin_ids:
            logger.warning("no_admin_telegram_ids_configured", severity=severity)
            return []

        logger.info("sending_admin_alert", admin_count=len(admin_ids), severity=severity)

        results = []
        errors = []

        for admin_id in admin_ids:
            try:
                result = await self.send_message(chat_id=admin_id, text=formatted_text, parse_mode="HTML")
                results.append(result)
            except TelegramAPIError as e:
                # Log but don't fail if one admin can't be reached
                logger.error("admin_alert_failed", admin_id=admin_id, error=str(e))
                errors.append({"admin_id": admin_id, "error": str(e)})

        logger.info(
            "admin_alert_complete",
            success_count=len(results),
            failure_count=len(errors),
            severity=severity,
        )

        return results

    async def get_me(self) -> dict[str, Any]:
        """Get information about the bot (health check endpoint).

        Returns:
            Bot information dictionary with id, username, first_name, etc.

        Raises:
            TelegramAPIError: On API errors
        """
        logger.debug("telegram_get_me_called")
        result = await self._make_request("GET", "getMe")
        logger.info(
            "telegram_bot_info_retrieved",
            bot_id=result.get("id"),
            bot_username=result.get("username"),
        )
        return result

    async def health_check(self) -> bool:
        """Perform a health check by calling getMe.

        Returns:
            True if bot is reachable and responding, False otherwise
        """
        try:
            await self.get_me()
            logger.info("telegram_health_check_passed")
            return True
        except Exception as e:
            logger.error("telegram_health_check_failed", error=str(e))
            return False
