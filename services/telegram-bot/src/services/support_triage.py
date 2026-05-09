"""Stage 1 Telegram support first-line triage.

This is intentionally deterministic for S1: it gives a predictable first-line
answer, routes risky cases to support, and avoids sending raw configs or tokens
into support notes.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum


class SupportCategory(StrEnum):
    PAYMENT = "payment"
    PROVISIONING = "provisioning"
    CONNECTIVITY = "connectivity"
    ACCOUNT = "account"
    LEGAL_ABUSE = "legal_abuse"
    GENERAL = "general"


class SupportPriority(StrEnum):
    P0 = "p0"
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"


@dataclass(frozen=True)
class SupportTriageResult:
    category: SupportCategory
    priority: SupportPriority
    first_line_reply_key: str
    support_reference: str
    safe_summary: str
    escalate: bool

    def to_escalation_payload(
        self,
        *,
        telegram_username: str | None,
    ) -> dict[str, object]:
        return {
            "support_reference": self.support_reference,
            "category": self.category.value,
            "priority": self.priority.value,
            "safe_summary": self.safe_summary,
            "first_line_reply_key": self.first_line_reply_key,
            "source": "telegram_bot",
            "telegram_username": telegram_username,
        }


_CONFIG_URL_PATTERN = re.compile(r"\b(?:vless|vmess|trojan|ss|wireguard)://[^\s<>]+", re.IGNORECASE)
_HTTP_URL_PATTERN = re.compile(r"\bhttps?://[^\s<>]+", re.IGNORECASE)
_TELEGRAM_BOT_TOKEN_PATTERN = re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{20,}\b")
_LONG_SECRET_PATTERN = re.compile(r"\b[A-Za-z0-9_-]{40,}\b")
_WHITESPACE_PATTERN = re.compile(r"\s+")

_PAYMENT_KEYWORDS = (
    "paid",
    "payment",
    "invoice",
    "refund",
    "chargeback",
    "card",
    "stars",
    "cryptobot",
    "yookassa",
    "payram",
    "nowpayments",
    "digiseller",
    "оплат",
    "платеж",
    "платёж",
    "возврат",
    "списал",
    "деньг",
    "карта",
    "звезд",
    "звёзд",
)
_PROVISIONING_KEYWORDS = (
    "config",
    "configuration",
    "subscription url",
    "qr",
    "access",
    "provision",
    "no access",
    "not ready",
    "конфиг",
    "конфигурац",
    "ссылк",
    "qr",
    "доступ",
    "не выдал",
    "не приш",
    "не получил",
)
_CONNECTIVITY_KEYWORDS = (
    "connect",
    "connection",
    "disconnect",
    "does not work",
    "not working",
    "no internet",
    "slow",
    "ping",
    "server",
    "подключ",
    "соедин",
    "не работает",
    "нет интернета",
    "медлен",
    "сервер",
)
_ACCOUNT_KEYWORDS = (
    "login",
    "password",
    "email",
    "telegram link",
    "account",
    "sign in",
    "войти",
    "логин",
    "пароль",
    "почта",
    "аккаунт",
    "привяз",
)
_LEGAL_ABUSE_KEYWORDS = (
    "law enforcement",
    "abuse",
    "malware",
    "spam",
    "police",
    "legal",
    "правоохран",
    "абуз",
    "жалоб",
    "спам",
    "вирус",
    "юрид",
)
_ESCALATION_KEYWORDS = (
    "operator",
    "human",
    "support",
    "agent",
    "urgent",
    "оператор",
    "человек",
    "поддерж",
    "срочно",
)


def redact_sensitive_support_text(value: str, *, max_chars: int = 500) -> str:
    """Return a compact support-safe summary without configs, URLs, or tokens."""
    redacted = _CONFIG_URL_PATTERN.sub("[vpn-config-url]", value)
    redacted = _TELEGRAM_BOT_TOKEN_PATTERN.sub("[telegram-token]", redacted)
    redacted = _HTTP_URL_PATTERN.sub("[url]", redacted)
    redacted = _LONG_SECRET_PATTERN.sub("[secret]", redacted)
    redacted = _WHITESPACE_PATTERN.sub(" ", redacted).strip()
    if len(redacted) <= max_chars:
        return redacted
    return f"{redacted[: max_chars - 3].rstrip()}..."


class Stage1SupportTriageService:
    """Classify Telegram support text into S1 support categories and priority."""

    def triage(self, *, text: str, telegram_id: int) -> SupportTriageResult:
        safe_summary = redact_sensitive_support_text(text)
        normalized = safe_summary.casefold()

        category = self._resolve_category(normalized)
        priority = self._resolve_priority(normalized, category)
        escalate = priority != SupportPriority.P3 or _contains_any(normalized, _ESCALATION_KEYWORDS)

        return SupportTriageResult(
            category=category,
            priority=priority,
            first_line_reply_key=f"support-first-line-{category.value}",
            support_reference=_support_reference(
                telegram_id=telegram_id,
                category=category,
                priority=priority,
                safe_summary=safe_summary,
            ),
            safe_summary=safe_summary,
            escalate=escalate,
        )

    @staticmethod
    def _resolve_category(normalized: str) -> SupportCategory:
        if _contains_any(normalized, _LEGAL_ABUSE_KEYWORDS):
            return SupportCategory.LEGAL_ABUSE
        if _contains_any(normalized, _PROVISIONING_KEYWORDS) and _contains_any(normalized, _PAYMENT_KEYWORDS):
            return SupportCategory.PROVISIONING
        if _contains_any(normalized, _PAYMENT_KEYWORDS):
            return SupportCategory.PAYMENT
        if _contains_any(normalized, _PROVISIONING_KEYWORDS):
            return SupportCategory.PROVISIONING
        if _contains_any(normalized, _CONNECTIVITY_KEYWORDS):
            return SupportCategory.CONNECTIVITY
        if _contains_any(normalized, _ACCOUNT_KEYWORDS):
            return SupportCategory.ACCOUNT
        return SupportCategory.GENERAL

    @staticmethod
    def _resolve_priority(normalized: str, category: SupportCategory) -> SupportPriority:
        if category == SupportCategory.LEGAL_ABUSE:
            return SupportPriority.P0
        if category in {SupportCategory.PAYMENT, SupportCategory.PROVISIONING}:
            return SupportPriority.P1
        if category in {SupportCategory.CONNECTIVITY, SupportCategory.ACCOUNT}:
            return SupportPriority.P2
        if _contains_any(normalized, _ESCALATION_KEYWORDS):
            return SupportPriority.P2
        return SupportPriority.P3


def _contains_any(value: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in value for keyword in keywords)


def _support_reference(
    *,
    telegram_id: int,
    category: SupportCategory,
    priority: SupportPriority,
    safe_summary: str,
) -> str:
    digest = hashlib.sha256(f"{telegram_id}:{category.value}:{priority.value}:{safe_summary}".encode()).hexdigest()
    return f"tg-{category.value}-{priority.value}-{digest[:12]}"
