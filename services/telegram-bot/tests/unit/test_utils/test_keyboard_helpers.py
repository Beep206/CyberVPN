"""Unit tests for keyboard helper utilities."""

from __future__ import annotations

from src.utils.keyboard_helpers import custom_emoji, icon_button


class TestCustomEmoji:
    """Test custom emoji HTML helper."""

    def test_custom_emoji_uses_telegram_spec_attribute_name(self) -> None:
        """Helper must emit ``emoji-id`` to match Telegram and aiogram 3.27+."""
        assert custom_emoji("1234567890", "🔥") == '<tg-emoji emoji-id="1234567890">🔥</tg-emoji>'

    def test_custom_emoji_falls_back_to_plain_text(self) -> None:
        """Helper returns the fallback when no custom emoji ID is provided."""
        assert custom_emoji(None, "🔥") == "🔥"


class TestIconButton:
    """Test inline keyboard button helper."""

    def test_icon_button_passes_icon_custom_emoji_id_and_style(self) -> None:
        """Button helper should forward aiogram 3.26+ styling parameters unchanged."""
        button = icon_button(
            text="Profile",
            callback_data="account:profile",
            icon_emoji_id="987654321",
            style="primary",
        )

        assert button.text == "Profile"
        assert button.callback_data == "account:profile"
        assert button.icon_custom_emoji_id == "987654321"
        assert button.style == "primary"

