"""FSM states for subscription flow."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class SubscriptionStates(StatesGroup):
    """
    State group for subscription purchase flow.

    Flow:
        1. selecting_plan: User selects a subscription plan (free/basic/premium/enterprise)
        2. selecting_duration: User selects subscription duration (7/30/90/365 days)
        3. selecting_payment: User selects payment method (crypto/card/etc)
        4. confirming: User confirms the purchase before payment
        5. processing: Payment is being processed (transitional state)
    """

    selecting_plan = State()
    selecting_duration = State()
    selecting_payment = State()
    confirming = State()
    processing = State()


class SubscriptionManagementStates(StatesGroup):
    """
    State group for managing existing subscriptions.

    Flow:
        1. viewing: Viewing subscription details
        2. renewing: Renewing an expiring subscription
        3. upgrading: Upgrading to a better plan
        4. cancelling: Confirming subscription cancellation
    """

    viewing = State()
    renewing = State()
    upgrading = State()
    cancelling = State()


class ServerSelectionStates(StatesGroup):
    """
    State group for selecting and configuring VPN servers.

    Flow:
        1. selecting_region: User selects geographic region
        2. selecting_server: User selects specific server from region
        3. selecting_protocol: User selects VPN protocol (WireGuard/OpenVPN/etc)
        4. configuring: User configures connection settings
    """

    selecting_region = State()
    selecting_server = State()
    selecting_protocol = State()
    configuring = State()
