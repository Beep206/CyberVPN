from src.config.settings import settings
from src.presentation.api.v1.client_capabilities.routes import _build_client_capabilities


def test_client_capabilities_hide_growth_hub_when_runtime_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "payments_enabled", False)
    monkeypatch.setattr(settings, "telegram_stars_enabled", True)
    monkeypatch.setattr(settings, "payment_autorenewal_enabled", False)
    monkeypatch.setattr(settings, "stage1_addons_enabled", False)
    monkeypatch.setattr(settings, "stage1_trial_provisioning_enabled", True)
    monkeypatch.setattr(settings, "stage1_paid_provisioning_enabled", True)
    monkeypatch.setattr(settings, "promo_codes_enabled", False)
    monkeypatch.setattr(settings, "gift_codes_enabled", False)
    monkeypatch.setattr(settings, "checkout_code_discounts_enabled", False)

    response = _build_client_capabilities(referral_runtime_enabled=False)

    assert response.payments.web_checkout is False
    assert response.payments.telegram_stars is True
    assert response.payments.manual_invoice is True
    assert response.growth.referral is False
    assert response.growth.gift_codes is False
    assert response.growth.growth_hub is False
    assert response.subscriptions.trial is True
    assert response.subscriptions.paid_provisioning is True


def test_client_capabilities_expose_enabled_growth_and_partner_flags(monkeypatch) -> None:
    monkeypatch.setattr(settings, "payments_enabled", True)
    monkeypatch.setattr(settings, "telegram_stars_enabled", True)
    monkeypatch.setattr(settings, "payment_autorenewal_enabled", False)
    monkeypatch.setattr(settings, "stage1_addons_enabled", True)
    monkeypatch.setattr(settings, "stage1_trial_provisioning_enabled", True)
    monkeypatch.setattr(settings, "stage1_paid_provisioning_enabled", True)
    monkeypatch.setattr(settings, "promo_codes_enabled", True)
    monkeypatch.setattr(settings, "gift_codes_enabled", True)
    monkeypatch.setattr(settings, "checkout_code_discounts_enabled", True)
    monkeypatch.setattr(settings, "partner_portal_enabled", True)
    monkeypatch.setattr(settings, "partner_payouts_enabled", False)

    response = _build_client_capabilities(referral_runtime_enabled=True)

    assert response.payments.web_checkout is True
    assert response.payments.cryptobot is True
    assert response.payments.manual_invoice is False
    assert response.growth.referral is True
    assert response.growth.promo_codes is True
    assert response.growth.gift_codes is True
    assert response.growth.checkout_code_discounts is True
    assert response.growth.growth_hub is True
    assert response.subscriptions.addons is True
    assert response.partner.portal is True
    assert response.partner.payouts is False
