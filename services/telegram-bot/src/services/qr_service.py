"""QR code generation service for subscriptions and referrals."""

from __future__ import annotations

from io import BytesIO
from typing import Literal

import qrcode
import qrcode.constants
import structlog

from ..utils.constants import (
    QR_CODE_BORDER,
    QR_CODE_BOX_SIZE,
    QR_CODE_ERROR_CORRECTION,
    QR_CODE_VERSION,
)

logger = structlog.get_logger(__name__)

# Map error correction levels
ERROR_CORRECTION_MAP = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H,
}


def generate_qr_code(
    data: str,
    version: int | None = QR_CODE_VERSION,
    error_correction: Literal["L", "M", "Q", "H"] = QR_CODE_ERROR_CORRECTION,  # type: ignore
    box_size: int = QR_CODE_BOX_SIZE,
    border: int = QR_CODE_BORDER,
    fill_color: str = "black",
    back_color: str = "white",
    image_format: Literal["PNG", "JPEG"] = "PNG",
) -> BytesIO:
    """
    Generate a QR code image.

    Args:
        data: Data to encode in QR code (URL, text, etc.)
        version: QR code version (1-40, None for auto)
        error_correction: Error correction level (L, M, Q, H)
        box_size: Size of each box in pixels
        border: Border size in boxes
        fill_color: Foreground color
        back_color: Background color
        image_format: Output image format

    Returns:
        BytesIO buffer containing the QR code image

    Examples:
        >>> qr_buffer = generate_qr_code("https://t.me/cybervpn_bot?start=ref123")
        >>> # Can be sent directly via bot.send_photo()

    Raises:
        ValueError: If QR code generation fails
    """
    try:
        # Get error correction level
        error_correction_level = ERROR_CORRECTION_MAP.get(
            error_correction.upper(),
            qrcode.constants.ERROR_CORRECT_H,
        )

        # Create QR code instance
        qr = qrcode.QRCode(
            version=version,
            error_correction=error_correction_level,
            box_size=box_size,
            border=border,
        )

        # Add data
        qr.add_data(data)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(
            fill_color=fill_color,
            back_color=back_color,
        )

        # Save to BytesIO
        buffer = BytesIO()
        img.save(buffer, format=image_format)
        buffer.seek(0)

        logger.info(
            "qr_code_generated",
            data_length=len(data),
            version=qr.version,
            size=f"{img.size[0]}x{img.size[1]}",
        )

        return buffer

    except Exception as e:
        logger.error("qr_code_generation_failed", error=str(e), data_length=len(data))
        raise ValueError(f"Failed to generate QR code: {e}") from e


def generate_subscription_qr(
    subscription_url: str,
    **kwargs,
) -> BytesIO:
    """
    Generate a QR code for a VPN subscription configuration.

    Args:
        subscription_url: VPN subscription URL or config string
        **kwargs: Additional arguments for generate_qr_code

    Returns:
        BytesIO buffer containing the QR code

    Examples:
        >>> url = "vmess://eyJhZGQiOiIxMjcuMC4wLjEiLCJwb3J0Ijo0NDMsInBzIjoiVVMtMDEifQ=="
        >>> qr = generate_subscription_qr(url)
    """
    logger.debug("generating_subscription_qr", url_length=len(subscription_url))
    return generate_qr_code(subscription_url, **kwargs)


def generate_referral_qr(
    referral_link: str,
    **kwargs,
) -> BytesIO:
    """
    Generate a QR code for a referral link.

    Args:
        referral_link: Telegram deep link for referral
        **kwargs: Additional arguments for generate_qr_code

    Returns:
        BytesIO buffer containing the QR code

    Examples:
        >>> link = "https://t.me/cybervpn_bot?start=ref123"
        >>> qr = generate_referral_qr(link)
    """
    logger.debug("generating_referral_qr", link=referral_link)

    # Use medium error correction for referral links (they're shorter)
    kwargs.setdefault("error_correction", "M")

    return generate_qr_code(referral_link, **kwargs)
