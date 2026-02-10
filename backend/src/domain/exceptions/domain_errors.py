from typing import Any


class DomainError(Exception):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# Entity not found errors
class UserNotFoundError(DomainError):
    def __init__(self, identifier: str | None = None) -> None:
        msg = f"User not found: {identifier}" if identifier else "User not found"
        super().__init__(msg, {"identifier": identifier})


class ServerNotFoundError(DomainError):
    def __init__(self, identifier: str | None = None) -> None:
        msg = f"Server not found: {identifier}" if identifier else "Server not found"
        super().__init__(msg, {"identifier": identifier})


class PaymentNotFoundError(DomainError):
    def __init__(self, identifier: str | None = None) -> None:
        msg = f"Payment not found: {identifier}" if identifier else "Payment not found"
        super().__init__(msg, {"identifier": identifier})


class InvoiceNotFoundError(DomainError):
    def __init__(self, identifier: str | None = None) -> None:
        msg = f"Invoice not found: {identifier}" if identifier else "Invoice not found"
        super().__init__(msg, {"identifier": identifier})


# Auth errors
class InvalidCredentialsError(DomainError):
    def __init__(self) -> None:
        super().__init__("Invalid credentials provided")


class InvalidTokenError(DomainError):
    def __init__(self, detail: str | None = None) -> None:
        msg = f"Invalid token: {detail}" if detail else "Invalid or expired token"
        super().__init__(msg, {"detail": detail})


class InsufficientPermissionsError(DomainError):
    def __init__(self, required_role: str | None = None) -> None:
        msg = f"Insufficient permissions. Required: {required_role}" if required_role else "Insufficient permissions"
        super().__init__(msg, {"required_role": required_role})


# Business rule violations
class UserAlreadyExistsError(DomainError):
    def __init__(self, identifier: str | None = None) -> None:
        msg = f"User already exists: {identifier}" if identifier else "User already exists"
        super().__init__(msg, {"identifier": identifier})


class DuplicateUsernameError(DomainError):
    def __init__(self, username: str | None = None) -> None:
        msg = f"Username already exists: {username}" if username else "Username already exists"
        super().__init__(msg, {"username": username})


class SubscriptionExpiredError(DomainError):
    def __init__(self, user_id: str | None = None) -> None:
        msg = f"Subscription expired for user: {user_id}" if user_id else "Subscription expired"
        super().__init__(msg, {"user_id": user_id})


class TrafficLimitExceededError(DomainError):
    def __init__(self, user_id: str | None = None) -> None:
        msg = f"Traffic limit exceeded for user: {user_id}" if user_id else "Traffic limit exceeded"
        super().__init__(msg, {"user_id": user_id})


class InvalidWebhookSignatureError(DomainError):
    def __init__(self) -> None:
        super().__init__("Invalid webhook signature")


class ValidationError(DomainError):
    def __init__(self, message: str = "Validation error", details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details)


# --- Codes & Wallet system errors ---


class InviteCodeNotFoundError(DomainError):
    def __init__(self, code: str | None = None) -> None:
        msg = f"Invite code not found: {code}" if code else "Invite code not found"
        super().__init__(msg, {"code": code})


class InviteCodeAlreadyUsedError(DomainError):
    def __init__(self, code: str | None = None) -> None:
        msg = f"Invite code already used: {code}" if code else "Invite code already used"
        super().__init__(msg, {"code": code})


class InviteCodeExpiredError(DomainError):
    def __init__(self, code: str | None = None) -> None:
        msg = f"Invite code expired: {code}" if code else "Invite code expired"
        super().__init__(msg, {"code": code})


class PromoCodeNotFoundError(DomainError):
    def __init__(self, code: str | None = None) -> None:
        msg = f"Promo code not found: {code}" if code else "Promo code not found"
        super().__init__(msg, {"code": code})


class PromoCodeInvalidError(DomainError):
    def __init__(self, reason: str | None = None) -> None:
        msg = f"Promo code invalid: {reason}" if reason else "Promo code is not valid"
        super().__init__(msg, {"reason": reason})


class PromoCodeExhaustedError(DomainError):
    def __init__(self, code: str | None = None) -> None:
        msg = f"Promo code usage limit reached: {code}" if code else "Promo code usage limit reached"
        super().__init__(msg, {"code": code})


class PartnerCodeNotFoundError(DomainError):
    def __init__(self, code: str | None = None) -> None:
        msg = f"Partner code not found: {code}" if code else "Partner code not found"
        super().__init__(msg, {"code": code})


class NotAPartnerError(DomainError):
    def __init__(self, identifier: str | None = None) -> None:
        msg = f"User is not a partner: {identifier}" if identifier else "User is not a partner"
        super().__init__(msg, {"identifier": identifier})


class MarkupExceedsLimitError(DomainError):
    def __init__(self, markup_pct: float | None = None, max_pct: float | None = None) -> None:
        msg = f"Markup {markup_pct}% exceeds maximum {max_pct}%"
        super().__init__(msg, {"markup_pct": markup_pct, "max_pct": max_pct})


class UserAlreadyBoundToPartnerError(DomainError):
    def __init__(self, identifier: str | None = None) -> None:
        msg = f"User already bound to a partner: {identifier}" if identifier else "User already bound to a partner"
        super().__init__(msg, {"identifier": identifier})


class WalletNotFoundError(DomainError):
    def __init__(self, identifier: str | None = None) -> None:
        msg = f"Wallet not found: {identifier}" if identifier else "Wallet not found"
        super().__init__(msg, {"identifier": identifier})


class InsufficientWalletBalanceError(DomainError):
    def __init__(self, available: str | None = None, required: str | None = None) -> None:
        msg = f"Insufficient wallet balance: available {available}, required {required}"
        super().__init__(msg, {"available": available, "required": required})


class WithdrawalBelowMinimumError(DomainError):
    def __init__(self, amount: str | None = None, minimum: str | None = None) -> None:
        msg = f"Withdrawal amount {amount} below minimum {minimum}"
        super().__init__(msg, {"amount": amount, "minimum": minimum})
