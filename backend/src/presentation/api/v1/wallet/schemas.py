"""Pydantic v2 schemas for the wallet API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WalletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    balance: float
    currency: str
    frozen: float


class WalletTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    amount: float
    balance_after: float
    reason: str
    description: str | None
    created_at: datetime


class WithdrawRequest(BaseModel):
    amount: float
    method: str = "cryptobot"


class WithdrawalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount: float
    currency: str
    method: str
    status: str
    created_at: datetime


class AdminTopupRequest(BaseModel):
    amount: float
    description: str | None = None


class AdminProcessWithdrawalRequest(BaseModel):
    admin_note: str | None = None
