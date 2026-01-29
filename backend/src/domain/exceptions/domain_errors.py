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
