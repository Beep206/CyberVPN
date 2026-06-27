from __future__ import annotations

from dataclasses import dataclass

from fastapi import status


@dataclass(frozen=True, slots=True)
class GrowthCustomerError:
    status_code: int
    code: str
    message_key: str
    retryable: bool = False

    def detail(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message_key": self.message_key,
            "retryable": self.retryable,
        }


_PRIVATE_GRANT_MESSAGE_KEYS = {
    "PRIVATE_CATALOG_GRANT_REQUIRES_QUOTE_SESSION": "growth.privateCatalog.errors.quoteSessionRequired",
    "PRIVATE_CATALOG_GRANT_REQUIRED": "growth.privateCatalog.errors.grantRequired",
    "PRIVATE_CATALOG_GRANT_CONTEXT_REQUIRED": "growth.privateCatalog.errors.contextRequired",
    "PRIVATE_CATALOG_GRANT_INVALID": "growth.privateCatalog.errors.grantInvalid",
    "PRIVATE_CATALOG_GRANT_SUBJECT_MISMATCH": "growth.privateCatalog.errors.subjectMismatch",
    "PRIVATE_CATALOG_GRANT_SCOPE_MISMATCH": "growth.privateCatalog.errors.scopeMismatch",
    "PRIVATE_OFFER_UNAVAILABLE": "growth.privateCatalog.errors.offerUnavailable",
    "PRIVATE_CATALOG_GRANT_EXHAUSTED": "growth.privateCatalog.errors.grantExhausted",
    "PRIVATE_CATALOG_GRANT_NOT_APPLICABLE": "growth.privateCatalog.errors.grantNotApplicable",
}

_PRIVATE_GRANT_STATUS_CODES = {
    "PRIVATE_CATALOG_GRANT_REQUIRES_QUOTE_SESSION": status.HTTP_400_BAD_REQUEST,
    "PRIVATE_CATALOG_GRANT_CONTEXT_REQUIRED": status.HTTP_400_BAD_REQUEST,
    "PRIVATE_CATALOG_GRANT_NOT_APPLICABLE": status.HTTP_400_BAD_REQUEST,
}

_FX_MESSAGE_KEYS = {
    "FX_RATE_UNAVAILABLE": "growth.fx.errors.rateUnavailable",
    "FX_XTR_MANAGED_RATE_REQUIRED": "growth.fx.errors.managedXtrRateRequired",
    "FX_RATE_SNAPSHOT_INVALID": "growth.fx.errors.rateSnapshotInvalid",
    "FX_AMOUNT_NEGATIVE": "growth.fx.errors.amountInvalid",
    "FX_CURRENCY_INVALID": "growth.fx.errors.currencyInvalid",
}

_FX_STATUS_CODES = {
    "FX_RATE_UNAVAILABLE": status.HTTP_409_CONFLICT,
    "FX_XTR_MANAGED_RATE_REQUIRED": status.HTTP_409_CONFLICT,
    "FX_RATE_SNAPSHOT_INVALID": status.HTTP_409_CONFLICT,
    "FX_AMOUNT_NEGATIVE": status.HTTP_400_BAD_REQUEST,
    "FX_CURRENCY_INVALID": status.HTTP_400_BAD_REQUEST,
}


def growth_customer_error_from_value_error(exc: ValueError) -> GrowthCustomerError | None:
    message = str(exc)
    if message == "CODE_SET_REJECTED":
        return GrowthCustomerError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="CODE_SET_REJECTED",
            message_key="growth.codes.errors.codeSetRejected",
        )
    if message == "codes cannot be combined with code_input, promo_code, or partner_code":
        return GrowthCustomerError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="GROWTH_CODE_INPUT_CONFLICT",
            message_key="growth.codes.errors.mixedInputs",
        )
    if message == "codes supports at most 5 entries":
        return GrowthCustomerError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="GROWTH_CODE_BASKET_TOO_LARGE",
            message_key="growth.codes.errors.tooManyCodes",
        )
    if message == "codes entries cannot be empty":
        return GrowthCustomerError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="GROWTH_CODE_EMPTY",
            message_key="growth.codes.errors.emptyCode",
        )
    if message == "codes entries cannot exceed 64 characters":
        return GrowthCustomerError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="GROWTH_CODE_TOO_LONG",
            message_key="growth.codes.errors.codeTooLong",
        )
    private_message_key = _PRIVATE_GRANT_MESSAGE_KEYS.get(message)
    if private_message_key is not None:
        return GrowthCustomerError(
            status_code=_PRIVATE_GRANT_STATUS_CODES.get(message, status.HTTP_409_CONFLICT),
            code=message,
            message_key=private_message_key,
        )
    fx_message_key = _FX_MESSAGE_KEYS.get(message)
    if fx_message_key is not None:
        return GrowthCustomerError(
            status_code=_FX_STATUS_CODES.get(message, status.HTTP_409_CONFLICT),
            code=message,
            message_key=fx_message_key,
        )
    return None
