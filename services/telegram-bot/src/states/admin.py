"""CyberVPN Telegram Bot — Admin FSM states.

StatesGroup definitions for all admin workflows including broadcast,
user management, promocodes, plans, access settings, and more.
"""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class BroadcastStates(StatesGroup):
    """Broadcast message creation flow."""

    composing_message = State()
    selecting_audience = State()
    editing_content = State()
    editing_buttons = State()
    previewing = State()
    confirming = State()


class UserManagementStates(StatesGroup):
    """Admin user management flow."""

    searching = State()
    searching_user = State()
    viewing_user = State()
    editing_discount = State()
    editing_points = State()
    editing_role = State()
    sending_message = State()
    editing_traffic = State()
    editing_devices = State()
    editing_expiry = State()
    extending_subscription = State()
    confirming_action = State()


class PromocodeManagementStates(StatesGroup):
    """Promocode CRUD flow."""

    listing = State()
    creating = State()
    creating_code = State()
    creating_discount = State()
    creating_limit = State()
    editing_code = State()
    editing_type = State()
    editing_reward = State()
    editing_availability = State()
    editing_limit = State()
    editing_users = State()
    editing_expiry = State()
    confirming = State()


class PlanManagementStates(StatesGroup):
    """Subscription plan management flow."""

    listing = State()
    creating = State()
    creating_name = State()
    creating_price = State()
    creating_description = State()
    editing_name = State()
    editing_description = State()
    editing_tag = State()
    editing_type = State()
    editing_availability = State()
    editing_traffic = State()
    editing_devices = State()
    editing_durations = State()
    editing_prices = State()
    confirming = State()


class AccessSettingsStates(StatesGroup):
    """Bot access configuration flow."""

    viewing = State()
    adding_admin = State()
    removing_admin = State()
    editing_mode = State()
    editing_rules_url = State()
    editing_channel_id = State()
    confirming = State()


class GatewaySettingsStates(StatesGroup):
    """Payment gateway configuration flow."""

    viewing = State()
    editing_cryptobot = State()
    editing_yookassa = State()
    editing_stars = State()
    confirming = State()


class ReferralSettingsStates(StatesGroup):
    """Referral system settings flow."""

    viewing = State()
    editing_bonus = State()
    editing_withdrawal = State()
    editing_max_referrals = State()
    editing_enabled = State()
    confirming = State()


class NotificationSettingsStates(StatesGroup):
    """Notification settings flow."""

    viewing = State()
    editing_expiry_days = State()
    editing_traffic_threshold = State()
    editing_enabled = State()
    confirming = State()


class ImportSyncStates(StatesGroup):
    """Import/sync data flow."""

    selecting_source = State()
    confirming_import = State()
    processing = State()
    viewing_results = State()


AdminBroadcastState = BroadcastStates
AdminUserState = UserManagementStates
AdminPromoState = PromocodeManagementStates
AdminPlanState = PlanManagementStates
AdminAccessState = AccessSettingsStates
AdminReferralSettingsState = ReferralSettingsStates
AdminNotificationSettingsState = NotificationSettingsStates
