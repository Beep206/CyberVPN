from __future__ import annotations

from src.services.support_triage import (
    Stage1SupportTriageService,
    SupportCategory,
    SupportPriority,
    redact_sensitive_support_text,
)


def test_support_triage_escalates_paid_no_access_without_leaking_config_url() -> None:
    result = Stage1SupportTriageService().triage(
        text="I paid with CryptoBot but got no access vless://secret-config",
        telegram_id=123456,
    )

    assert result.category == SupportCategory.PROVISIONING
    assert result.priority == SupportPriority.P1
    assert result.escalate is True
    assert result.support_reference.startswith("tg-provisioning-p1-")
    assert "vless://" not in result.safe_summary
    assert "[vpn-config-url]" in result.safe_summary


def test_support_triage_keeps_general_question_as_first_line_only() -> None:
    result = Stage1SupportTriageService().triage(
        text="What plans are available in beta?",
        telegram_id=123456,
    )

    assert result.category == SupportCategory.GENERAL
    assert result.priority == SupportPriority.P3
    assert result.escalate is False


def test_redact_sensitive_support_text_removes_urls_tokens_and_long_values() -> None:
    redacted = redact_sensitive_support_text(
        "Use https://example.com/a and 123456789:"
        "AAAA_BBBBBBBBBBBBBBBBBBBBBBBB "
        "plus ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    )

    assert "https://example.com" not in redacted
    assert "123456789:" not in redacted
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" not in redacted
    assert "[url]" in redacted
    assert "[telegram-token]" in redacted
    assert "[secret]" in redacted
