from dataclasses import dataclass
from decimal import Decimal

_VALID_CURRENCIES = {"USD", "RUB", "EUR", "GBP", "USDT", "TON"}


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if self.currency not in _VALID_CURRENCIES:
            raise ValueError(f"Invalid currency: {self.currency}. Must be one of {_VALID_CURRENCIES}")
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"
