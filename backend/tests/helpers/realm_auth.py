from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.presentation.dependencies.database import get_db


class FakeRedis:
    def __init__(self) -> None:
        self._values: dict[str, object] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._expiry: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        value = int(self._values.get(key, 0)) + 1
        self._values[key] = value
        return value

    async def expire(self, key: str, ttl_seconds: int) -> bool:
        self._expiry[key] = ttl_seconds
        return True

    async def set(self, key: str, value: object) -> bool:
        self._values[key] = value
        return True

    async def setex(self, key: str, ttl_seconds: int, value: object) -> bool:
        self._values[key] = value
        self._expiry[key] = ttl_seconds
        return True

    async def get(self, key: str) -> object | None:
        return self._values.get(key)

    async def exists(self, key: str) -> int:
        return 1 if key in self._values or key in self._hashes else 0

    async def ttl(self, key: str) -> int:
        return self._expiry.get(key, -1)

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self._values:
                del self._values[key]
                deleted += 1
            if key in self._hashes:
                del self._hashes[key]
                deleted += 1
            self._expiry.pop(key, None)
        return deleted

    async def hset(self, key: str, field: str, value: str) -> int:
        bucket = self._hashes.setdefault(key, {})
        bucket[field] = value
        return 1

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._hashes.get(key, {}))

    async def hdel(self, key: str, *fields: str) -> int:
        bucket = self._hashes.get(key, {})
        deleted = 0
        for field in fields:
            if field in bucket:
                del bucket[field]
                deleted += 1
        return deleted

    async def scan_iter(self, match: str | None = None, count: int | None = None):
        _ = count
        prefix = None
        if match and match.endswith("*"):
            prefix = match[:-1]

        keys = list(self._values) + list(self._hashes)
        for key in keys:
            if prefix is None or key.startswith(prefix):
                yield key


class SyncSessionAdapter:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, instance) -> None:
        self._session.add(instance)

    def add_all(self, instances) -> None:
        self._session.add_all(instances)

    async def execute(self, statement):
        return self._session.execute(statement)

    async def get(self, entity, ident):
        return self._session.get(entity, ident)

    async def flush(self) -> None:
        self._session.flush()

    async def commit(self) -> None:
        self._session.commit()

    async def rollback(self) -> None:
        self._session.rollback()

    async def merge(self, instance):
        return self._session.merge(instance)

    async def delete(self, instance) -> None:
        self._session.delete(instance)

    async def refresh(self, instance) -> None:
        self._session.refresh(instance)


def create_realm_test_sessionmaker() -> tuple[sessionmaker[Session], object, Path]:
    temp_file = NamedTemporaryFile(prefix="cybervpn-realm-auth-", suffix=".sqlite3", delete=False)
    temp_file.close()
    sqlite_path = Path(temp_file.name)
    engine = create_engine(f"sqlite:///{sqlite_path}", future=True)
    factory = sessionmaker(engine, class_=Session, expire_on_commit=False)
    return factory, engine, sqlite_path


async def initialize_realm_test_database(engine) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE auth_realms (
                id TEXT PRIMARY KEY,
                realm_key TEXT NOT NULL UNIQUE,
                realm_type TEXT NOT NULL,
                display_name TEXT NOT NULL,
                audience TEXT NOT NULL UNIQUE,
                cookie_namespace TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                is_default INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE brands (
                id TEXT PRIMARY KEY,
                brand_key TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE invoice_profiles (
                id TEXT PRIMARY KEY,
                profile_key TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                issuer_legal_name TEXT NOT NULL,
                tax_identifier TEXT,
                issuer_email TEXT,
                tax_behavior TEXT NOT NULL DEFAULT '{}',
                invoice_footer TEXT,
                receipt_footer TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE merchant_profiles (
                id TEXT PRIMARY KEY,
                profile_key TEXT NOT NULL UNIQUE,
                legal_entity_name TEXT NOT NULL,
                billing_descriptor TEXT NOT NULL,
                invoice_profile_id TEXT,
                settlement_reference TEXT,
                supported_currencies TEXT NOT NULL DEFAULT '[]',
                tax_behavior TEXT NOT NULL DEFAULT '{}',
                refund_responsibility_model TEXT NOT NULL DEFAULT 'merchant_of_record',
                chargeback_liability_model TEXT NOT NULL DEFAULT 'merchant_of_record',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (invoice_profile_id) REFERENCES invoice_profiles(id)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_merchant_profiles_invoice_profile_id "
            "ON merchant_profiles(invoice_profile_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE support_profiles (
                id TEXT PRIMARY KEY,
                profile_key TEXT NOT NULL UNIQUE,
                support_email TEXT NOT NULL,
                help_center_url TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE communication_profiles (
                id TEXT PRIMARY KEY,
                profile_key TEXT NOT NULL UNIQUE,
                sender_domain TEXT NOT NULL,
                from_email TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE storefronts (
                id TEXT PRIMARY KEY,
                storefront_key TEXT NOT NULL UNIQUE,
                brand_id TEXT NOT NULL,
                display_name TEXT NOT NULL,
                host TEXT NOT NULL UNIQUE,
                merchant_profile_id TEXT,
                auth_realm_id TEXT,
                support_profile_id TEXT,
                communication_profile_id TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (brand_id) REFERENCES brands(id),
                FOREIGN KEY (merchant_profile_id) REFERENCES merchant_profiles(id),
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (support_profile_id) REFERENCES support_profiles(id),
                FOREIGN KEY (communication_profile_id) REFERENCES communication_profiles(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_storefronts_auth_realm_id ON storefronts(auth_realm_id)")
        conn.exec_driver_sql(
            """
            CREATE TABLE billing_descriptors (
                id TEXT PRIMARY KEY,
                descriptor_key TEXT NOT NULL UNIQUE,
                merchant_profile_id TEXT NOT NULL,
                invoice_profile_id TEXT,
                statement_descriptor TEXT NOT NULL,
                soft_descriptor TEXT,
                support_phone TEXT,
                support_url TEXT,
                is_default INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (merchant_profile_id) REFERENCES merchant_profiles(id),
                FOREIGN KEY (invoice_profile_id) REFERENCES invoice_profiles(id)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_billing_descriptors_merchant_profile_id ON billing_descriptors(merchant_profile_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_billing_descriptors_invoice_profile_id ON billing_descriptors(invoice_profile_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE subscription_plans (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                tier TEXT,
                plan_code TEXT,
                display_name TEXT NOT NULL DEFAULT '',
                catalog_visibility TEXT NOT NULL DEFAULT 'hidden',
                duration_days INTEGER NOT NULL,
                traffic_limit_bytes INTEGER,
                device_limit INTEGER NOT NULL DEFAULT 1,
                price_usd NUMERIC NOT NULL,
                price_rub NUMERIC,
                sale_channels TEXT NOT NULL DEFAULT '[]',
                traffic_policy TEXT NOT NULL DEFAULT '{}',
                connection_modes TEXT NOT NULL DEFAULT '[]',
                server_pool TEXT NOT NULL DEFAULT '[]',
                support_sla TEXT NOT NULL DEFAULT 'standard',
                dedicated_ip TEXT NOT NULL DEFAULT '{}',
                invite_bundle TEXT NOT NULL DEFAULT '{}',
                trial_eligible INTEGER NOT NULL DEFAULT 0,
                features TEXT NOT NULL DEFAULT '{}',
                is_active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_subscription_plans_plan_code ON subscription_plans(plan_code)")
        conn.exec_driver_sql(
            """
            CREATE TABLE offer_versions (
                id TEXT PRIMARY KEY,
                offer_key TEXT NOT NULL,
                display_name TEXT NOT NULL,
                subscription_plan_id TEXT NOT NULL,
                included_addon_codes TEXT NOT NULL DEFAULT '[]',
                sale_channels TEXT NOT NULL DEFAULT '[]',
                visibility_rules TEXT NOT NULL DEFAULT '{}',
                invite_bundle TEXT NOT NULL DEFAULT '{}',
                trial_eligible INTEGER NOT NULL DEFAULT 0,
                gift_eligible INTEGER NOT NULL DEFAULT 0,
                referral_eligible INTEGER NOT NULL DEFAULT 0,
                renewal_incentives TEXT NOT NULL DEFAULT '{}',
                version_status TEXT NOT NULL DEFAULT 'active',
                effective_from TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                effective_to TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subscription_plan_id) REFERENCES subscription_plans(id),
                UNIQUE (offer_key, effective_from)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_offer_versions_offer_key ON offer_versions(offer_key)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_offer_versions_subscription_plan_id "
            "ON offer_versions(subscription_plan_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_offer_versions_version_status ON offer_versions(version_status)")
        conn.exec_driver_sql("CREATE INDEX ix_offer_versions_effective_from ON offer_versions(effective_from)")
        conn.exec_driver_sql(
            """
            CREATE TABLE pricebook_versions (
                id TEXT PRIMARY KEY,
                pricebook_key TEXT NOT NULL,
                display_name TEXT NOT NULL,
                storefront_id TEXT NOT NULL,
                merchant_profile_id TEXT,
                currency_code TEXT NOT NULL DEFAULT 'USD',
                region_code TEXT,
                discount_rules TEXT NOT NULL DEFAULT '{}',
                renewal_pricing_policy TEXT NOT NULL DEFAULT '{}',
                version_status TEXT NOT NULL DEFAULT 'active',
                effective_from TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                effective_to TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id),
                FOREIGN KEY (merchant_profile_id) REFERENCES merchant_profiles(id),
                UNIQUE (pricebook_key, effective_from)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_pricebook_versions_pricebook_key ON pricebook_versions(pricebook_key)")
        conn.exec_driver_sql("CREATE INDEX ix_pricebook_versions_storefront_id ON pricebook_versions(storefront_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_pricebook_versions_merchant_profile_id ON pricebook_versions(merchant_profile_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_pricebook_versions_currency_code ON pricebook_versions(currency_code)")
        conn.exec_driver_sql("CREATE INDEX ix_pricebook_versions_region_code ON pricebook_versions(region_code)")
        conn.exec_driver_sql("CREATE INDEX ix_pricebook_versions_version_status ON pricebook_versions(version_status)")
        conn.exec_driver_sql("CREATE INDEX ix_pricebook_versions_effective_from ON pricebook_versions(effective_from)")
        conn.exec_driver_sql(
            """
            CREATE TABLE pricebook_entries (
                id TEXT PRIMARY KEY,
                pricebook_id TEXT NOT NULL,
                offer_id TEXT NOT NULL,
                visible_price NUMERIC NOT NULL,
                compare_at_price NUMERIC,
                included_addon_codes TEXT NOT NULL DEFAULT '[]',
                display_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pricebook_id) REFERENCES pricebook_versions(id),
                FOREIGN KEY (offer_id) REFERENCES offer_versions(id),
                UNIQUE (pricebook_id, offer_id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_pricebook_entries_pricebook_id ON pricebook_entries(pricebook_id)")
        conn.exec_driver_sql("CREATE INDEX ix_pricebook_entries_offer_id ON pricebook_entries(offer_id)")
        conn.exec_driver_sql(
            """
            CREATE TABLE program_eligibility_versions (
                id TEXT PRIMARY KEY,
                policy_key TEXT NOT NULL,
                subject_type TEXT NOT NULL,
                subscription_plan_id TEXT,
                plan_addon_id TEXT,
                offer_id TEXT,
                invite_allowed INTEGER NOT NULL DEFAULT 0,
                referral_credit_allowed INTEGER NOT NULL DEFAULT 0,
                creator_affiliate_allowed INTEGER NOT NULL DEFAULT 0,
                performance_allowed INTEGER NOT NULL DEFAULT 0,
                reseller_allowed INTEGER NOT NULL DEFAULT 0,
                renewal_commissionable INTEGER NOT NULL DEFAULT 0,
                addon_commissionable INTEGER NOT NULL DEFAULT 0,
                version_status TEXT NOT NULL DEFAULT 'active',
                effective_from TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                effective_to TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subscription_plan_id) REFERENCES subscription_plans(id),
                FOREIGN KEY (offer_id) REFERENCES offer_versions(id),
                UNIQUE (policy_key, effective_from)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_program_eligibility_versions_policy_key ON program_eligibility_versions(policy_key)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_program_eligibility_versions_subject_type ON program_eligibility_versions(subject_type)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_program_eligibility_versions_subscription_plan_id "
            "ON program_eligibility_versions(subscription_plan_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_program_eligibility_versions_offer_id ON program_eligibility_versions(offer_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_program_eligibility_versions_version_status "
            "ON program_eligibility_versions(version_status)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_program_eligibility_versions_effective_from "
            "ON program_eligibility_versions(effective_from)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE admin_users (
                id TEXT PRIMARY KEY,
                login TEXT NOT NULL,
                email TEXT,
                auth_realm_id TEXT,
                password_hash TEXT,
                role TEXT NOT NULL DEFAULT 'viewer',
                telegram_id INTEGER,
                is_active INTEGER NOT NULL DEFAULT 1,
                totp_secret TEXT,
                totp_enabled INTEGER NOT NULL DEFAULT 0,
                backup_codes_hash TEXT,
                anti_phishing_code TEXT,
                last_login_at TEXT,
                last_login_ip TEXT,
                failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                password_changed_at TEXT,
                sign_in_count INTEGER NOT NULL DEFAULT 0,
                current_sign_in_at TEXT,
                current_sign_in_ip TEXT,
                last_active_at TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                ban_reason TEXT,
                fraud_score INTEGER NOT NULL DEFAULT 0,
                risk_level TEXT NOT NULL DEFAULT 'low',
                tos_accepted_at TEXT,
                marketing_consent INTEGER NOT NULL DEFAULT 0,
                referred_by_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_email_verified INTEGER NOT NULL DEFAULT 0,
                deleted_at TEXT,
                trial_activated_at TEXT,
                trial_expires_at TEXT,
                display_name TEXT,
                language TEXT NOT NULL DEFAULT 'en',
                timezone TEXT NOT NULL DEFAULT 'UTC',
                notification_prefs TEXT,
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                UNIQUE (auth_realm_id, login),
                UNIQUE (auth_realm_id, email)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_admin_users_login ON admin_users(login)")
        conn.exec_driver_sql("CREATE INDEX ix_admin_users_email ON admin_users(email)")
        conn.exec_driver_sql("CREATE INDEX ix_admin_users_auth_realm_id ON admin_users(auth_realm_id)")
        conn.exec_driver_sql(
            """
            CREATE TABLE refresh_tokens (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                revoked_at TEXT,
                device_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                last_used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES admin_users(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens(user_id)")
        conn.exec_driver_sql("CREATE INDEX ix_refresh_tokens_token_hash ON refresh_tokens(token_hash)")
        conn.exec_driver_sql(
            """
            CREATE TABLE system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE mobile_users (
                id TEXT PRIMARY KEY,
                auth_realm_id TEXT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                username TEXT UNIQUE,
                telegram_id INTEGER UNIQUE,
                telegram_username TEXT,
                remnawave_uuid TEXT UNIQUE,
                subscription_url TEXT,
                referral_code TEXT UNIQUE,
                referred_by_user_id TEXT,
                partner_user_id TEXT,
                partner_account_id TEXT,
                is_partner INTEGER NOT NULL DEFAULT 0,
                partner_promoted_at TEXT,
                trial_activated_at TEXT,
                trial_expires_at TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_login_at TEXT,
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (referred_by_user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (partner_user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_mobile_users_auth_realm_id ON mobile_users(auth_realm_id)")
        conn.exec_driver_sql("CREATE INDEX ix_mobile_users_partner_account_id ON mobile_users(partner_account_id)")
        conn.exec_driver_sql(
            """
            CREATE TABLE wallets (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                balance NUMERIC NOT NULL DEFAULT 0,
                currency TEXT NOT NULL DEFAULT 'USD',
                frozen NUMERIC NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_wallets_user_id ON wallets(user_id)")
        conn.exec_driver_sql(
            """
            CREATE TABLE wallet_transactions (
                id TEXT PRIMARY KEY,
                wallet_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                amount NUMERIC NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                balance_after NUMERIC NOT NULL,
                reason TEXT NOT NULL,
                reference_type TEXT,
                reference_id TEXT,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_wallet_transactions_wallet_id ON wallet_transactions(wallet_id)")
        conn.exec_driver_sql("CREATE INDEX ix_wallet_transactions_user_id ON wallet_transactions(user_id)")
        conn.exec_driver_sql("CREATE INDEX ix_wallet_transactions_created_at ON wallet_transactions(created_at)")
        conn.exec_driver_sql(
            """
            CREATE TABLE invite_codes (
                id TEXT PRIMARY KEY,
                code TEXT NOT NULL UNIQUE,
                owner_user_id TEXT NOT NULL,
                free_days INTEGER NOT NULL,
                plan_id TEXT,
                source TEXT NOT NULL,
                source_payment_id TEXT,
                is_used INTEGER NOT NULL DEFAULT 0,
                used_by_user_id TEXT,
                used_at TEXT,
                expires_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_invite_codes_code ON invite_codes(code)")
        conn.exec_driver_sql("CREATE INDEX ix_invite_codes_owner_user_id ON invite_codes(owner_user_id)")
        conn.exec_driver_sql("CREATE INDEX ix_invite_codes_used_by_user_id ON invite_codes(used_by_user_id)")
        conn.exec_driver_sql(
            """
            CREATE TABLE promo_codes (
                id TEXT PRIMARY KEY,
                code TEXT NOT NULL UNIQUE,
                discount_type TEXT NOT NULL,
                discount_value NUMERIC NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                max_uses INTEGER,
                current_uses INTEGER NOT NULL DEFAULT 0,
                is_single_use INTEGER NOT NULL DEFAULT 0,
                plan_ids TEXT,
                min_amount NUMERIC,
                expires_at TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                description TEXT,
                created_by TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_promo_codes_code ON promo_codes(code)")
        conn.exec_driver_sql(
            """
            CREATE TABLE promo_code_usages (
                id TEXT PRIMARY KEY,
                promo_code_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                payment_id TEXT NOT NULL,
                discount_applied NUMERIC NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_promo_code_usages_promo_code_id ON promo_code_usages(promo_code_id)")
        conn.exec_driver_sql("CREATE INDEX ix_promo_code_usages_user_id ON promo_code_usages(user_id)")
        conn.exec_driver_sql(
            """
            CREATE TABLE policy_versions (
                id TEXT PRIMARY KEY,
                policy_family TEXT NOT NULL,
                policy_key TEXT NOT NULL,
                subject_type TEXT NOT NULL,
                subject_id TEXT,
                version_number INTEGER NOT NULL,
                payload TEXT NOT NULL,
                approval_state TEXT NOT NULL DEFAULT 'draft',
                version_status TEXT NOT NULL DEFAULT 'draft',
                effective_from TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                effective_to TEXT,
                created_by_admin_user_id TEXT,
                approved_by_admin_user_id TEXT,
                approved_at TEXT,
                rejection_reason TEXT,
                supersedes_policy_version_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (approved_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (supersedes_policy_version_id) REFERENCES policy_versions(id),
                UNIQUE (policy_family, policy_key, version_number)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_policy_versions_policy_family ON policy_versions(policy_family)")
        conn.exec_driver_sql("CREATE INDEX ix_policy_versions_policy_key ON policy_versions(policy_key)")
        conn.exec_driver_sql("CREATE INDEX ix_policy_versions_subject_type ON policy_versions(subject_type)")
        conn.exec_driver_sql("CREATE INDEX ix_policy_versions_subject_id ON policy_versions(subject_id)")
        conn.exec_driver_sql("CREATE INDEX ix_policy_versions_approval_state ON policy_versions(approval_state)")
        conn.exec_driver_sql("CREATE INDEX ix_policy_versions_version_status ON policy_versions(version_status)")
        conn.exec_driver_sql("CREATE INDEX ix_policy_versions_effective_from ON policy_versions(effective_from)")
        conn.exec_driver_sql(
            """
            CREATE TABLE legal_documents (
                id TEXT PRIMARY KEY,
                document_key TEXT NOT NULL,
                document_type TEXT NOT NULL,
                locale TEXT NOT NULL DEFAULT 'en-EN',
                title TEXT NOT NULL,
                content_markdown TEXT NOT NULL,
                content_checksum TEXT NOT NULL,
                policy_version_id TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (policy_version_id) REFERENCES policy_versions(id),
                UNIQUE (document_key, locale, policy_version_id)
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE storefront_legal_doc_sets (
                id TEXT PRIMARY KEY,
                set_key TEXT NOT NULL,
                storefront_id TEXT NOT NULL,
                auth_realm_id TEXT,
                display_name TEXT NOT NULL,
                policy_version_id TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id),
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (policy_version_id) REFERENCES policy_versions(id),
                UNIQUE (set_key, policy_version_id)
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE storefront_legal_doc_set_items (
                id TEXT PRIMARY KEY,
                legal_document_set_id TEXT NOT NULL,
                legal_document_id TEXT NOT NULL,
                required INTEGER NOT NULL DEFAULT 1,
                display_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (legal_document_set_id) REFERENCES storefront_legal_doc_sets(id),
                FOREIGN KEY (legal_document_id) REFERENCES legal_documents(id),
                UNIQUE (legal_document_set_id, legal_document_id)
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE accepted_legal_documents (
                id TEXT PRIMARY KEY,
                legal_document_id TEXT,
                legal_document_set_id TEXT,
                storefront_id TEXT NOT NULL,
                auth_realm_id TEXT NOT NULL,
                actor_principal_id TEXT NOT NULL,
                actor_principal_type TEXT NOT NULL,
                acceptance_channel TEXT NOT NULL,
                quote_session_id TEXT,
                checkout_session_id TEXT,
                order_id TEXT,
                source_ip TEXT,
                user_agent TEXT,
                device_context TEXT,
                accepted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (legal_document_id) REFERENCES legal_documents(id),
                FOREIGN KEY (legal_document_set_id) REFERENCES storefront_legal_doc_sets(id),
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id),
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                CHECK (
                    (CASE WHEN legal_document_id IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN legal_document_set_id IS NOT NULL THEN 1 ELSE 0 END) = 1
                )
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_accepted_legal_documents_actor_principal_id "
            "ON accepted_legal_documents(actor_principal_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE mobile_devices (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                device_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                platform_id TEXT,
                os_version TEXT,
                app_version TEXT,
                device_model TEXT,
                push_token TEXT,
                last_active_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_accounts (
                id TEXT PRIMARY KEY,
                account_key TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                legacy_owner_user_id TEXT,
                created_by_admin_user_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (legacy_owner_user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_partner_accounts_account_key ON partner_accounts(account_key)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_accounts_legacy_owner_user_id ON partner_accounts(legacy_owner_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_accounts_created_by_admin_user_id ON partner_accounts(created_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_account_roles (
                id TEXT PRIMARY KEY,
                role_key TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                description TEXT NOT NULL,
                permission_keys TEXT NOT NULL,
                is_system INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_account_users (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL,
                admin_user_id TEXT NOT NULL,
                role_id TEXT NOT NULL,
                membership_status TEXT NOT NULL DEFAULT 'active',
                invited_by_admin_user_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (role_id) REFERENCES partner_account_roles(id),
                FOREIGN KEY (invited_by_admin_user_id) REFERENCES admin_users(id),
                UNIQUE (partner_account_id, admin_user_id)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_account_users_partner_account_id ON partner_account_users(partner_account_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_account_users_admin_user_id ON partner_account_users(admin_user_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_partner_account_users_role_id ON partner_account_users(role_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_account_users_invited_by_admin_user_id "
            "ON partner_account_users(invited_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_traffic_declarations (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL,
                declaration_kind TEXT NOT NULL,
                declaration_status TEXT NOT NULL DEFAULT 'submitted',
                scope_label TEXT NOT NULL,
                declaration_payload TEXT NOT NULL DEFAULT '{}',
                notes_payload TEXT NOT NULL DEFAULT '[]',
                submitted_by_admin_user_id TEXT,
                reviewed_by_admin_user_id TEXT,
                reviewed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (submitted_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                FOREIGN KEY (reviewed_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_traffic_declarations_partner_account_id "
            "ON partner_traffic_declarations(partner_account_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_traffic_declarations_declaration_kind "
            "ON partner_traffic_declarations(declaration_kind)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_traffic_declarations_declaration_status "
            "ON partner_traffic_declarations(declaration_status)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_traffic_declarations_submitted_by_admin_user_id "
            "ON partner_traffic_declarations(submitted_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_traffic_declarations_reviewed_by_admin_user_id "
            "ON partner_traffic_declarations(reviewed_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_traffic_declarations_reviewed_at "
            "ON partner_traffic_declarations(reviewed_at)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE creative_approvals (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL,
                approval_kind TEXT NOT NULL,
                approval_status TEXT NOT NULL DEFAULT 'under_review',
                scope_label TEXT NOT NULL,
                creative_ref TEXT,
                approval_payload TEXT NOT NULL DEFAULT '{}',
                notes_payload TEXT NOT NULL DEFAULT '[]',
                submitted_by_admin_user_id TEXT,
                reviewed_by_admin_user_id TEXT,
                reviewed_at TEXT,
                expires_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (submitted_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                FOREIGN KEY (reviewed_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_creative_approvals_partner_account_id ON creative_approvals(partner_account_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_creative_approvals_approval_kind ON creative_approvals(approval_kind)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_creative_approvals_approval_status ON creative_approvals(approval_status)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_creative_approvals_creative_ref ON creative_approvals(creative_ref)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_creative_approvals_submitted_by_admin_user_id "
            "ON creative_approvals(submitted_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_creative_approvals_reviewed_by_admin_user_id "
            "ON creative_approvals(reviewed_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_creative_approvals_reviewed_at ON creative_approvals(reviewed_at)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_creative_approvals_expires_at ON creative_approvals(expires_at)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_integration_credentials (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL,
                credential_kind TEXT NOT NULL,
                credential_status TEXT NOT NULL DEFAULT 'pending_rotation',
                credential_hash TEXT NOT NULL,
                token_hint TEXT NOT NULL,
                scope_key TEXT NOT NULL,
                destination_ref TEXT,
                credential_metadata TEXT NOT NULL DEFAULT '{}',
                created_by_admin_user_id TEXT,
                rotated_by_admin_user_id TEXT,
                last_rotated_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                FOREIGN KEY (rotated_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                UNIQUE (partner_account_id, credential_kind)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_integration_credentials_partner_account_id "
            "ON partner_integration_credentials(partner_account_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_integration_credentials_credential_kind "
            "ON partner_integration_credentials(credential_kind)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_integration_credentials_credential_status "
            "ON partner_integration_credentials(credential_status)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_integration_credentials_credential_hash "
            "ON partner_integration_credentials(credential_hash)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_integration_credentials_created_by_admin_user_id "
            "ON partner_integration_credentials(created_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_integration_credentials_rotated_by_admin_user_id "
            "ON partner_integration_credentials(rotated_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_integration_credentials_last_rotated_at "
            "ON partner_integration_credentials(last_rotated_at)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_codes (
                id TEXT PRIMARY KEY,
                code TEXT NOT NULL UNIQUE,
                partner_account_id TEXT,
                partner_user_id TEXT NOT NULL,
                markup_pct NUMERIC NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (partner_user_id) REFERENCES mobile_users(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_partner_codes_partner_account_id ON partner_codes(partner_account_id)")
        conn.exec_driver_sql("CREATE INDEX ix_partner_codes_partner_user_id ON partner_codes(partner_user_id)")
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_earnings (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT,
                partner_user_id TEXT NOT NULL,
                client_user_id TEXT NOT NULL,
                payment_id TEXT NOT NULL,
                partner_code_id TEXT NOT NULL,
                base_price NUMERIC NOT NULL,
                markup_amount NUMERIC NOT NULL,
                commission_pct NUMERIC NOT NULL,
                commission_amount NUMERIC NOT NULL,
                total_earning NUMERIC NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                wallet_tx_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (partner_user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (client_user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (partner_code_id) REFERENCES partner_codes(id)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_earnings_partner_account_id ON partner_earnings(partner_account_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_partner_earnings_partner_user_id ON partner_earnings(partner_user_id)")
        conn.exec_driver_sql(
            """
            CREATE TABLE earning_events (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT,
                partner_user_id TEXT NOT NULL,
                client_user_id TEXT NOT NULL,
                order_id TEXT NOT NULL UNIQUE,
                payment_id TEXT,
                partner_code_id TEXT,
                legacy_partner_earning_id TEXT,
                order_attribution_result_id TEXT,
                owner_type TEXT NOT NULL,
                event_status TEXT NOT NULL DEFAULT 'on_hold',
                commission_base_amount NUMERIC NOT NULL,
                markup_amount NUMERIC NOT NULL,
                commission_pct NUMERIC NOT NULL,
                commission_amount NUMERIC NOT NULL,
                total_amount NUMERIC NOT NULL,
                currency_code TEXT NOT NULL DEFAULT 'USD',
                available_at TEXT,
                source_snapshot TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (partner_user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (client_user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (payment_id) REFERENCES payments(id),
                FOREIGN KEY (partner_code_id) REFERENCES partner_codes(id),
                FOREIGN KEY (legacy_partner_earning_id) REFERENCES partner_earnings(id),
                FOREIGN KEY (order_attribution_result_id) REFERENCES order_attribution_results(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_partner_account_id ON earning_events(partner_account_id)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_partner_user_id ON earning_events(partner_user_id)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_client_user_id ON earning_events(client_user_id)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_order_id ON earning_events(order_id)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_payment_id ON earning_events(payment_id)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_partner_code_id ON earning_events(partner_code_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_earning_events_legacy_partner_earning_id ON earning_events(legacy_partner_earning_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_earning_events_order_attribution_result_id "
            "ON earning_events(order_attribution_result_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_owner_type ON earning_events(owner_type)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_event_status ON earning_events(event_status)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_available_at ON earning_events(available_at)")
        conn.exec_driver_sql(
            """
            CREATE TABLE earning_holds (
                id TEXT PRIMARY KEY,
                earning_event_id TEXT NOT NULL,
                partner_account_id TEXT,
                hold_reason_type TEXT NOT NULL,
                hold_status TEXT NOT NULL DEFAULT 'active',
                reason_code TEXT,
                hold_until TEXT,
                released_at TEXT,
                released_by_admin_user_id TEXT,
                created_by_admin_user_id TEXT,
                hold_payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (earning_event_id) REFERENCES earning_events(id),
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (released_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_earning_holds_earning_event_id ON earning_holds(earning_event_id)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_holds_partner_account_id ON earning_holds(partner_account_id)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_holds_hold_reason_type ON earning_holds(hold_reason_type)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_holds_hold_status ON earning_holds(hold_status)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_holds_hold_until ON earning_holds(hold_until)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_holds_released_at ON earning_holds(released_at)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_earning_holds_released_by_admin_user_id ON earning_holds(released_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_earning_holds_created_by_admin_user_id ON earning_holds(created_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE reserves (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL,
                source_earning_event_id TEXT,
                reserve_scope TEXT NOT NULL,
                reserve_reason_type TEXT NOT NULL,
                reserve_status TEXT NOT NULL DEFAULT 'active',
                amount NUMERIC NOT NULL,
                currency_code TEXT NOT NULL DEFAULT 'USD',
                reason_code TEXT,
                reserve_payload TEXT NOT NULL DEFAULT '{}',
                released_at TEXT,
                released_by_admin_user_id TEXT,
                created_by_admin_user_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (source_earning_event_id) REFERENCES earning_events(id),
                FOREIGN KEY (released_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_reserves_partner_account_id ON reserves(partner_account_id)")
        conn.exec_driver_sql("CREATE INDEX ix_reserves_source_earning_event_id ON reserves(source_earning_event_id)")
        conn.exec_driver_sql("CREATE INDEX ix_reserves_reserve_scope ON reserves(reserve_scope)")
        conn.exec_driver_sql("CREATE INDEX ix_reserves_reserve_reason_type ON reserves(reserve_reason_type)")
        conn.exec_driver_sql("CREATE INDEX ix_reserves_reserve_status ON reserves(reserve_status)")
        conn.exec_driver_sql("CREATE INDEX ix_reserves_released_at ON reserves(released_at)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_reserves_released_by_admin_user_id ON reserves(released_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_reserves_created_by_admin_user_id ON reserves(created_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE settlement_periods (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL,
                period_key TEXT NOT NULL,
                period_status TEXT NOT NULL DEFAULT 'open',
                currency_code TEXT NOT NULL DEFAULT 'USD',
                window_start TEXT NOT NULL,
                window_end TEXT NOT NULL,
                closed_at TEXT,
                closed_by_admin_user_id TEXT,
                reopened_at TEXT,
                reopened_by_admin_user_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (closed_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (reopened_by_admin_user_id) REFERENCES admin_users(id),
                UNIQUE (partner_account_id, period_key)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_settlement_periods_partner_account_id ON settlement_periods(partner_account_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_settlement_periods_period_key ON settlement_periods(period_key)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_settlement_periods_window_start ON settlement_periods(window_start)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_settlement_periods_window_end ON settlement_periods(window_end)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_settlement_periods_closed_at ON settlement_periods(closed_at)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_settlement_periods_closed_by_admin_user_id ON settlement_periods(closed_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_settlement_periods_reopened_at ON settlement_periods(reopened_at)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_settlement_periods_reopened_by_admin_user_id "
            "ON settlement_periods(reopened_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_statements (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL,
                settlement_period_id TEXT NOT NULL,
                statement_key TEXT NOT NULL UNIQUE,
                statement_version INTEGER NOT NULL DEFAULT 1,
                statement_status TEXT NOT NULL DEFAULT 'open',
                reopened_from_statement_id TEXT,
                superseded_by_statement_id TEXT,
                currency_code TEXT NOT NULL DEFAULT 'USD',
                accrual_amount NUMERIC NOT NULL DEFAULT 0,
                on_hold_amount NUMERIC NOT NULL DEFAULT 0,
                reserve_amount NUMERIC NOT NULL DEFAULT 0,
                adjustment_net_amount NUMERIC NOT NULL DEFAULT 0,
                available_amount NUMERIC NOT NULL DEFAULT 0,
                source_event_count INTEGER NOT NULL DEFAULT 0,
                held_event_count INTEGER NOT NULL DEFAULT 0,
                active_reserve_count INTEGER NOT NULL DEFAULT 0,
                adjustment_count INTEGER NOT NULL DEFAULT 0,
                statement_snapshot TEXT NOT NULL DEFAULT '{}',
                closed_at TEXT,
                closed_by_admin_user_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (settlement_period_id) REFERENCES settlement_periods(id),
                FOREIGN KEY (reopened_from_statement_id) REFERENCES partner_statements(id),
                FOREIGN KEY (superseded_by_statement_id) REFERENCES partner_statements(id),
                FOREIGN KEY (closed_by_admin_user_id) REFERENCES admin_users(id),
                UNIQUE (partner_account_id, settlement_period_id, statement_version)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_statements_partner_account_id ON partner_statements(partner_account_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_statements_settlement_period_id ON partner_statements(settlement_period_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_statements_statement_key ON partner_statements(statement_key)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_statements_closed_at ON partner_statements(closed_at)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_statements_closed_by_admin_user_id ON partner_statements(closed_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_statements_reopened_from_statement_id "
            "ON partner_statements(reopened_from_statement_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_statements_superseded_by_statement_id "
            "ON partner_statements(superseded_by_statement_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE statement_adjustments (
                id TEXT PRIMARY KEY,
                partner_statement_id TEXT NOT NULL,
                partner_account_id TEXT NOT NULL,
                source_reference_type TEXT,
                source_reference_id TEXT,
                carried_from_adjustment_id TEXT,
                adjustment_type TEXT NOT NULL,
                adjustment_direction TEXT NOT NULL,
                amount NUMERIC NOT NULL,
                currency_code TEXT NOT NULL DEFAULT 'USD',
                reason_code TEXT,
                adjustment_payload TEXT NOT NULL DEFAULT '{}',
                created_by_admin_user_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_statement_id) REFERENCES partner_statements(id),
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (carried_from_adjustment_id) REFERENCES statement_adjustments(id),
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_statement_adjustments_partner_statement_id ON statement_adjustments(partner_statement_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_statement_adjustments_partner_account_id ON statement_adjustments(partner_account_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_statement_adjustments_source_reference_type "
            "ON statement_adjustments(source_reference_type)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_statement_adjustments_source_reference_id ON statement_adjustments(source_reference_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_statement_adjustments_carried_from_adjustment_id "
            "ON statement_adjustments(carried_from_adjustment_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_statement_adjustments_adjustment_type ON statement_adjustments(adjustment_type)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_statement_adjustments_created_by_admin_user_id "
            "ON statement_adjustments(created_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_payout_accounts (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL,
                settlement_profile_id TEXT,
                payout_rail TEXT NOT NULL,
                display_label TEXT NOT NULL,
                destination_reference TEXT NOT NULL,
                masked_destination TEXT NOT NULL,
                destination_metadata TEXT NOT NULL DEFAULT '{}',
                verification_status TEXT NOT NULL DEFAULT 'pending',
                approval_status TEXT NOT NULL DEFAULT 'pending',
                account_status TEXT NOT NULL DEFAULT 'active',
                is_default INTEGER NOT NULL DEFAULT 0,
                created_by_admin_user_id TEXT,
                verified_by_admin_user_id TEXT,
                verified_at TEXT,
                approved_by_admin_user_id TEXT,
                approved_at TEXT,
                suspended_by_admin_user_id TEXT,
                suspended_at TEXT,
                suspension_reason_code TEXT,
                archived_by_admin_user_id TEXT,
                archived_at TEXT,
                archive_reason_code TEXT,
                default_selected_by_admin_user_id TEXT,
                default_selected_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (verified_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (approved_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (suspended_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (archived_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (default_selected_by_admin_user_id) REFERENCES admin_users(id)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_partner_account_id "
            "ON partner_payout_accounts(partner_account_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_settlement_profile_id "
            "ON partner_payout_accounts(settlement_profile_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_payout_rail ON partner_payout_accounts(payout_rail)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_verification_status "
            "ON partner_payout_accounts(verification_status)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_approval_status "
            "ON partner_payout_accounts(approval_status)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_account_status "
            "ON partner_payout_accounts(account_status)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_created_by_admin_user_id "
            "ON partner_payout_accounts(created_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_verified_by_admin_user_id "
            "ON partner_payout_accounts(verified_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_verified_at "
            "ON partner_payout_accounts(verified_at)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_approved_by_admin_user_id "
            "ON partner_payout_accounts(approved_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_approved_at "
            "ON partner_payout_accounts(approved_at)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_suspended_by_admin_user_id "
            "ON partner_payout_accounts(suspended_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_suspended_at "
            "ON partner_payout_accounts(suspended_at)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_archived_by_admin_user_id "
            "ON partner_payout_accounts(archived_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_archived_at "
            "ON partner_payout_accounts(archived_at)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_default_selected_by_admin_user_id "
            "ON partner_payout_accounts(default_selected_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_default_selected_at "
            "ON partner_payout_accounts(default_selected_at)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE payout_instructions (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL,
                partner_statement_id TEXT NOT NULL UNIQUE,
                partner_payout_account_id TEXT NOT NULL,
                instruction_key TEXT NOT NULL UNIQUE,
                instruction_status TEXT NOT NULL DEFAULT 'pending_approval',
                payout_amount NUMERIC NOT NULL,
                currency_code TEXT NOT NULL DEFAULT 'USD',
                instruction_snapshot TEXT NOT NULL DEFAULT '{}',
                created_by_admin_user_id TEXT,
                approved_by_admin_user_id TEXT,
                approved_at TEXT,
                rejected_by_admin_user_id TEXT,
                rejected_at TEXT,
                rejection_reason_code TEXT,
                completed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (partner_statement_id) REFERENCES partner_statements(id),
                FOREIGN KEY (partner_payout_account_id) REFERENCES partner_payout_accounts(id),
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (approved_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (rejected_by_admin_user_id) REFERENCES admin_users(id)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_instructions_partner_account_id ON payout_instructions(partner_account_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_instructions_partner_statement_id ON payout_instructions(partner_statement_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_instructions_partner_payout_account_id "
            "ON payout_instructions(partner_payout_account_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_instructions_instruction_key ON payout_instructions(instruction_key)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_instructions_instruction_status ON payout_instructions(instruction_status)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_instructions_created_by_admin_user_id "
            "ON payout_instructions(created_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_instructions_approved_by_admin_user_id "
            "ON payout_instructions(approved_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_instructions_approved_at ON payout_instructions(approved_at)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_instructions_rejected_by_admin_user_id "
            "ON payout_instructions(rejected_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_instructions_rejected_at ON payout_instructions(rejected_at)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_instructions_completed_at ON payout_instructions(completed_at)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE payout_executions (
                id TEXT PRIMARY KEY,
                payout_instruction_id TEXT NOT NULL,
                partner_account_id TEXT NOT NULL,
                partner_statement_id TEXT NOT NULL,
                partner_payout_account_id TEXT NOT NULL,
                execution_key TEXT NOT NULL UNIQUE,
                execution_mode TEXT NOT NULL DEFAULT 'dry_run',
                execution_status TEXT NOT NULL DEFAULT 'requested',
                request_idempotency_key TEXT NOT NULL,
                external_reference TEXT,
                execution_payload TEXT NOT NULL DEFAULT '{}',
                result_payload TEXT NOT NULL DEFAULT '{}',
                requested_by_admin_user_id TEXT,
                submitted_by_admin_user_id TEXT,
                submitted_at TEXT,
                completed_by_admin_user_id TEXT,
                completed_at TEXT,
                reconciled_by_admin_user_id TEXT,
                reconciled_at TEXT,
                failure_reason_code TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (payout_instruction_id) REFERENCES payout_instructions(id),
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (partner_statement_id) REFERENCES partner_statements(id),
                FOREIGN KEY (partner_payout_account_id) REFERENCES partner_payout_accounts(id),
                FOREIGN KEY (requested_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (submitted_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (completed_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (reconciled_by_admin_user_id) REFERENCES admin_users(id),
                UNIQUE (payout_instruction_id, request_idempotency_key)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_payout_instruction_id "
            "ON payout_executions(payout_instruction_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_partner_account_id ON payout_executions(partner_account_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_partner_statement_id ON payout_executions(partner_statement_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_partner_payout_account_id "
            "ON payout_executions(partner_payout_account_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_execution_key ON payout_executions(execution_key)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_execution_mode ON payout_executions(execution_mode)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_execution_status ON payout_executions(execution_status)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_request_idempotency_key "
            "ON payout_executions(request_idempotency_key)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_external_reference ON payout_executions(external_reference)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_requested_by_admin_user_id "
            "ON payout_executions(requested_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_submitted_by_admin_user_id "
            "ON payout_executions(submitted_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_submitted_at ON payout_executions(submitted_at)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_completed_by_admin_user_id "
            "ON payout_executions(completed_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_completed_at ON payout_executions(completed_at)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_reconciled_by_admin_user_id "
            "ON payout_executions(reconciled_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_reconciled_at ON payout_executions(reconciled_at)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE principal_sessions (
                id TEXT PRIMARY KEY,
                auth_realm_id TEXT NOT NULL,
                principal_subject TEXT NOT NULL,
                principal_class TEXT NOT NULL,
                audience TEXT NOT NULL,
                scope_family TEXT NOT NULL,
                access_token_jti TEXT,
                refresh_token_id TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                issued_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (refresh_token_id) REFERENCES refresh_tokens(id)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_principal_sessions_principal_subject ON principal_sessions(principal_subject)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_principal_sessions_refresh_token_id ON principal_sessions(refresh_token_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE risk_subjects (
                id TEXT PRIMARY KEY,
                principal_class TEXT NOT NULL,
                principal_subject TEXT NOT NULL,
                auth_realm_id TEXT,
                storefront_id TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                risk_level TEXT NOT NULL DEFAULT 'low',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id),
                UNIQUE (principal_class, principal_subject, auth_realm_id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_risk_subjects_principal_class ON risk_subjects(principal_class)")
        conn.exec_driver_sql("CREATE INDEX ix_risk_subjects_principal_subject ON risk_subjects(principal_subject)")
        conn.exec_driver_sql("CREATE INDEX ix_risk_subjects_auth_realm_id ON risk_subjects(auth_realm_id)")
        conn.exec_driver_sql("CREATE INDEX ix_risk_subjects_storefront_id ON risk_subjects(storefront_id)")
        conn.exec_driver_sql(
            """
            CREATE TABLE risk_identifiers (
                id TEXT PRIMARY KEY,
                risk_subject_id TEXT NOT NULL,
                identifier_type TEXT NOT NULL,
                value_hash TEXT NOT NULL,
                value_preview TEXT NOT NULL,
                is_verified INTEGER NOT NULL DEFAULT 0,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (risk_subject_id) REFERENCES risk_subjects(id),
                UNIQUE (risk_subject_id, identifier_type, value_hash)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_risk_identifiers_risk_subject_id ON risk_identifiers(risk_subject_id)")
        conn.exec_driver_sql("CREATE INDEX ix_risk_identifiers_identifier_type ON risk_identifiers(identifier_type)")
        conn.exec_driver_sql("CREATE INDEX ix_risk_identifiers_value_hash ON risk_identifiers(value_hash)")
        conn.exec_driver_sql(
            """
            CREATE TABLE risk_links (
                id TEXT PRIMARY KEY,
                left_subject_id TEXT NOT NULL,
                right_subject_id TEXT NOT NULL,
                link_type TEXT NOT NULL,
                identifier_type TEXT NOT NULL,
                source_identifier_id TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                evidence TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (left_subject_id) REFERENCES risk_subjects(id),
                FOREIGN KEY (right_subject_id) REFERENCES risk_subjects(id),
                FOREIGN KEY (source_identifier_id) REFERENCES risk_identifiers(id),
                UNIQUE (left_subject_id, right_subject_id, identifier_type)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_risk_links_left_subject_id ON risk_links(left_subject_id)")
        conn.exec_driver_sql("CREATE INDEX ix_risk_links_right_subject_id ON risk_links(right_subject_id)")
        conn.exec_driver_sql("CREATE INDEX ix_risk_links_link_type ON risk_links(link_type)")
        conn.exec_driver_sql("CREATE INDEX ix_risk_links_identifier_type ON risk_links(identifier_type)")
        conn.exec_driver_sql("CREATE INDEX ix_risk_links_source_identifier_id ON risk_links(source_identifier_id)")
        conn.exec_driver_sql(
            """
            CREATE TABLE risk_reviews (
                id TEXT PRIMARY KEY,
                risk_subject_id TEXT NOT NULL,
                review_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                decision TEXT NOT NULL DEFAULT 'pending',
                reason TEXT NOT NULL,
                evidence TEXT NOT NULL DEFAULT '{}',
                created_by_admin_user_id TEXT,
                resolved_by_admin_user_id TEXT,
                resolved_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (risk_subject_id) REFERENCES risk_subjects(id),
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (resolved_by_admin_user_id) REFERENCES admin_users(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_risk_reviews_risk_subject_id ON risk_reviews(risk_subject_id)")
        conn.exec_driver_sql("CREATE INDEX ix_risk_reviews_review_type ON risk_reviews(review_type)")
        conn.exec_driver_sql("CREATE INDEX ix_risk_reviews_status ON risk_reviews(status)")
        conn.exec_driver_sql("CREATE INDEX ix_risk_reviews_decision ON risk_reviews(decision)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_risk_reviews_created_by_admin_user_id ON risk_reviews(created_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_risk_reviews_resolved_by_admin_user_id ON risk_reviews(resolved_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE risk_review_attachments (
                id TEXT PRIMARY KEY,
                risk_review_id TEXT NOT NULL,
                attachment_type TEXT NOT NULL,
                storage_key TEXT NOT NULL UNIQUE,
                file_name TEXT,
                attachment_metadata TEXT NOT NULL DEFAULT '{}',
                created_by_admin_user_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (risk_review_id) REFERENCES risk_reviews(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_risk_review_attachments_risk_review_id "
            "ON risk_review_attachments(risk_review_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_risk_review_attachments_attachment_type "
            "ON risk_review_attachments(attachment_type)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_risk_review_attachments_created_by_admin_user_id "
            "ON risk_review_attachments(created_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE governance_actions (
                id TEXT PRIMARY KEY,
                risk_subject_id TEXT NOT NULL,
                risk_review_id TEXT,
                action_type TEXT NOT NULL,
                action_status TEXT NOT NULL DEFAULT 'requested',
                target_type TEXT,
                target_ref TEXT,
                reason TEXT NOT NULL,
                action_payload TEXT NOT NULL DEFAULT '{}',
                created_by_admin_user_id TEXT,
                applied_by_admin_user_id TEXT,
                applied_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (risk_subject_id) REFERENCES risk_subjects(id) ON DELETE CASCADE,
                FOREIGN KEY (risk_review_id) REFERENCES risk_reviews(id) ON DELETE SET NULL,
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                FOREIGN KEY (applied_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_governance_actions_risk_subject_id ON governance_actions(risk_subject_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_governance_actions_risk_review_id ON governance_actions(risk_review_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_governance_actions_action_type ON governance_actions(action_type)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_governance_actions_action_status ON governance_actions(action_status)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_governance_actions_target_type ON governance_actions(target_type)")
        conn.exec_driver_sql("CREATE INDEX ix_governance_actions_target_ref ON governance_actions(target_ref)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_governance_actions_created_by_admin_user_id "
            "ON governance_actions(created_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_governance_actions_applied_by_admin_user_id "
            "ON governance_actions(applied_by_admin_user_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_governance_actions_applied_at ON governance_actions(applied_at)")
        conn.exec_driver_sql(
            """
            CREATE TABLE quote_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                auth_realm_id TEXT NOT NULL,
                storefront_id TEXT NOT NULL,
                merchant_profile_id TEXT,
                invoice_profile_id TEXT,
                billing_descriptor_id TEXT,
                pricebook_id TEXT,
                pricebook_entry_id TEXT,
                offer_id TEXT,
                legal_document_set_id TEXT,
                program_eligibility_policy_id TEXT,
                subscription_plan_id TEXT,
                sale_channel TEXT NOT NULL DEFAULT 'web',
                currency_code TEXT NOT NULL DEFAULT 'USD',
                quote_status TEXT NOT NULL DEFAULT 'open',
                promo_code TEXT,
                promo_code_id TEXT,
                partner_code_id TEXT,
                request_snapshot TEXT NOT NULL DEFAULT '{}',
                quote_snapshot TEXT NOT NULL DEFAULT '{}',
                context_snapshot TEXT NOT NULL DEFAULT '{}',
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id),
                FOREIGN KEY (merchant_profile_id) REFERENCES merchant_profiles(id),
                FOREIGN KEY (invoice_profile_id) REFERENCES invoice_profiles(id),
                FOREIGN KEY (billing_descriptor_id) REFERENCES billing_descriptors(id),
                FOREIGN KEY (pricebook_id) REFERENCES pricebook_versions(id),
                FOREIGN KEY (pricebook_entry_id) REFERENCES pricebook_entries(id),
                FOREIGN KEY (offer_id) REFERENCES offer_versions(id),
                FOREIGN KEY (legal_document_set_id) REFERENCES storefront_legal_doc_sets(id),
                FOREIGN KEY (program_eligibility_policy_id) REFERENCES program_eligibility_versions(id),
                FOREIGN KEY (subscription_plan_id) REFERENCES subscription_plans(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_quote_sessions_user_id ON quote_sessions(user_id)")
        conn.exec_driver_sql("CREATE INDEX ix_quote_sessions_auth_realm_id ON quote_sessions(auth_realm_id)")
        conn.exec_driver_sql("CREATE INDEX ix_quote_sessions_storefront_id ON quote_sessions(storefront_id)")
        conn.exec_driver_sql("CREATE INDEX ix_quote_sessions_quote_status ON quote_sessions(quote_status)")
        conn.exec_driver_sql("CREATE INDEX ix_quote_sessions_expires_at ON quote_sessions(expires_at)")
        conn.exec_driver_sql(
            """
            CREATE TABLE checkout_sessions (
                id TEXT PRIMARY KEY,
                quote_session_id TEXT NOT NULL UNIQUE,
                user_id TEXT NOT NULL,
                auth_realm_id TEXT NOT NULL,
                storefront_id TEXT NOT NULL,
                merchant_profile_id TEXT,
                invoice_profile_id TEXT,
                billing_descriptor_id TEXT,
                pricebook_id TEXT,
                pricebook_entry_id TEXT,
                offer_id TEXT,
                legal_document_set_id TEXT,
                program_eligibility_policy_id TEXT,
                subscription_plan_id TEXT,
                sale_channel TEXT NOT NULL DEFAULT 'web',
                currency_code TEXT NOT NULL DEFAULT 'USD',
                checkout_status TEXT NOT NULL DEFAULT 'open',
                idempotency_key TEXT NOT NULL,
                promo_code_id TEXT,
                partner_code_id TEXT,
                request_snapshot TEXT NOT NULL DEFAULT '{}',
                checkout_snapshot TEXT NOT NULL DEFAULT '{}',
                context_snapshot TEXT NOT NULL DEFAULT '{}',
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quote_session_id) REFERENCES quote_sessions(id),
                FOREIGN KEY (user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id),
                FOREIGN KEY (merchant_profile_id) REFERENCES merchant_profiles(id),
                FOREIGN KEY (invoice_profile_id) REFERENCES invoice_profiles(id),
                FOREIGN KEY (billing_descriptor_id) REFERENCES billing_descriptors(id),
                FOREIGN KEY (pricebook_id) REFERENCES pricebook_versions(id),
                FOREIGN KEY (pricebook_entry_id) REFERENCES pricebook_entries(id),
                FOREIGN KEY (offer_id) REFERENCES offer_versions(id),
                FOREIGN KEY (legal_document_set_id) REFERENCES storefront_legal_doc_sets(id),
                FOREIGN KEY (program_eligibility_policy_id) REFERENCES program_eligibility_versions(id),
                FOREIGN KEY (subscription_plan_id) REFERENCES subscription_plans(id)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_checkout_sessions_quote_session_id "
            "ON checkout_sessions(quote_session_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_checkout_sessions_user_id ON checkout_sessions(user_id)")
        conn.exec_driver_sql("CREATE INDEX ix_checkout_sessions_auth_realm_id ON checkout_sessions(auth_realm_id)")
        conn.exec_driver_sql("CREATE INDEX ix_checkout_sessions_storefront_id ON checkout_sessions(storefront_id)")
        conn.exec_driver_sql("CREATE INDEX ix_checkout_sessions_checkout_status ON checkout_sessions(checkout_status)")
        conn.exec_driver_sql("CREATE INDEX ix_checkout_sessions_idempotency_key ON checkout_sessions(idempotency_key)")
        conn.exec_driver_sql("CREATE INDEX ix_checkout_sessions_expires_at ON checkout_sessions(expires_at)")
        conn.exec_driver_sql(
            """
            CREATE TABLE orders (
                id TEXT PRIMARY KEY,
                quote_session_id TEXT,
                checkout_session_id TEXT NOT NULL UNIQUE,
                user_id TEXT NOT NULL,
                auth_realm_id TEXT NOT NULL,
                storefront_id TEXT NOT NULL,
                merchant_profile_id TEXT,
                invoice_profile_id TEXT,
                billing_descriptor_id TEXT,
                pricebook_id TEXT,
                pricebook_entry_id TEXT,
                offer_id TEXT,
                legal_document_set_id TEXT,
                program_eligibility_policy_id TEXT,
                subscription_plan_id TEXT,
                promo_code_id TEXT,
                partner_code_id TEXT,
                sale_channel TEXT NOT NULL DEFAULT 'web',
                currency_code TEXT NOT NULL DEFAULT 'USD',
                order_status TEXT NOT NULL DEFAULT 'committed',
                settlement_status TEXT NOT NULL DEFAULT 'pending_payment',
                base_price NUMERIC NOT NULL,
                addon_amount NUMERIC NOT NULL DEFAULT 0,
                displayed_price NUMERIC NOT NULL,
                discount_amount NUMERIC NOT NULL DEFAULT 0,
                wallet_amount NUMERIC NOT NULL DEFAULT 0,
                gateway_amount NUMERIC NOT NULL DEFAULT 0,
                partner_markup NUMERIC NOT NULL DEFAULT 0,
                commission_base_amount NUMERIC NOT NULL DEFAULT 0,
                merchant_snapshot TEXT NOT NULL DEFAULT '{}',
                pricing_snapshot TEXT NOT NULL DEFAULT '{}',
                policy_snapshot TEXT NOT NULL DEFAULT '{}',
                entitlements_snapshot TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quote_session_id) REFERENCES quote_sessions(id),
                FOREIGN KEY (checkout_session_id) REFERENCES checkout_sessions(id),
                FOREIGN KEY (user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id),
                FOREIGN KEY (merchant_profile_id) REFERENCES merchant_profiles(id),
                FOREIGN KEY (invoice_profile_id) REFERENCES invoice_profiles(id),
                FOREIGN KEY (billing_descriptor_id) REFERENCES billing_descriptors(id),
                FOREIGN KEY (pricebook_id) REFERENCES pricebook_versions(id),
                FOREIGN KEY (pricebook_entry_id) REFERENCES pricebook_entries(id),
                FOREIGN KEY (offer_id) REFERENCES offer_versions(id),
                FOREIGN KEY (legal_document_set_id) REFERENCES storefront_legal_doc_sets(id),
                FOREIGN KEY (program_eligibility_policy_id) REFERENCES program_eligibility_versions(id),
                FOREIGN KEY (subscription_plan_id) REFERENCES subscription_plans(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_orders_quote_session_id ON orders(quote_session_id)")
        conn.exec_driver_sql("CREATE INDEX ix_orders_checkout_session_id ON orders(checkout_session_id)")
        conn.exec_driver_sql("CREATE INDEX ix_orders_user_id ON orders(user_id)")
        conn.exec_driver_sql("CREATE INDEX ix_orders_auth_realm_id ON orders(auth_realm_id)")
        conn.exec_driver_sql("CREATE INDEX ix_orders_storefront_id ON orders(storefront_id)")
        conn.exec_driver_sql("CREATE INDEX ix_orders_merchant_profile_id ON orders(merchant_profile_id)")
        conn.exec_driver_sql("CREATE INDEX ix_orders_invoice_profile_id ON orders(invoice_profile_id)")
        conn.exec_driver_sql("CREATE INDEX ix_orders_billing_descriptor_id ON orders(billing_descriptor_id)")
        conn.exec_driver_sql("CREATE INDEX ix_orders_pricebook_id ON orders(pricebook_id)")
        conn.exec_driver_sql("CREATE INDEX ix_orders_pricebook_entry_id ON orders(pricebook_entry_id)")
        conn.exec_driver_sql("CREATE INDEX ix_orders_offer_id ON orders(offer_id)")
        conn.exec_driver_sql("CREATE INDEX ix_orders_legal_document_set_id ON orders(legal_document_set_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_orders_program_eligibility_policy_id ON orders(program_eligibility_policy_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_orders_subscription_plan_id ON orders(subscription_plan_id)")
        conn.exec_driver_sql("CREATE INDEX ix_orders_promo_code_id ON orders(promo_code_id)")
        conn.exec_driver_sql("CREATE INDEX ix_orders_partner_code_id ON orders(partner_code_id)")
        conn.exec_driver_sql("CREATE INDEX ix_orders_order_status ON orders(order_status)")
        conn.exec_driver_sql("CREATE INDEX ix_orders_settlement_status ON orders(settlement_status)")
        conn.exec_driver_sql(
            """
            CREATE TABLE order_items (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                item_type TEXT NOT NULL,
                subject_id TEXT,
                subject_code TEXT,
                display_name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                unit_price NUMERIC NOT NULL,
                total_price NUMERIC NOT NULL,
                currency_code TEXT NOT NULL DEFAULT 'USD',
                item_snapshot TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_order_items_order_id ON order_items(order_id)")
        conn.exec_driver_sql("CREATE INDEX ix_order_items_item_type ON order_items(item_type)")
        conn.exec_driver_sql("CREATE INDEX ix_order_items_subject_id ON order_items(subject_id)")
        conn.exec_driver_sql("CREATE INDEX ix_order_items_subject_code ON order_items(subject_code)")
        conn.exec_driver_sql(
            """
            CREATE TABLE attribution_touchpoints (
                id TEXT PRIMARY KEY,
                touchpoint_type TEXT NOT NULL,
                user_id TEXT,
                auth_realm_id TEXT,
                storefront_id TEXT,
                quote_session_id TEXT,
                checkout_session_id TEXT,
                order_id TEXT,
                partner_code_id TEXT,
                sale_channel TEXT,
                source_host TEXT,
                source_path TEXT,
                campaign_params TEXT NOT NULL DEFAULT '{}',
                evidence_payload TEXT NOT NULL DEFAULT '{}',
                occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id),
                FOREIGN KEY (quote_session_id) REFERENCES quote_sessions(id),
                FOREIGN KEY (checkout_session_id) REFERENCES checkout_sessions(id),
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (partner_code_id) REFERENCES partner_codes(id)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_attribution_touchpoints_touchpoint_type ON attribution_touchpoints(touchpoint_type)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_attribution_touchpoints_user_id ON attribution_touchpoints(user_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_attribution_touchpoints_auth_realm_id ON attribution_touchpoints(auth_realm_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_attribution_touchpoints_storefront_id ON attribution_touchpoints(storefront_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_attribution_touchpoints_quote_session_id ON attribution_touchpoints(quote_session_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_attribution_touchpoints_checkout_session_id "
            "ON attribution_touchpoints(checkout_session_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_attribution_touchpoints_order_id ON attribution_touchpoints(order_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_attribution_touchpoints_partner_code_id ON attribution_touchpoints(partner_code_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_attribution_touchpoints_sale_channel ON attribution_touchpoints(sale_channel)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_attribution_touchpoints_occurred_at ON attribution_touchpoints(occurred_at)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE customer_commercial_bindings (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                auth_realm_id TEXT NOT NULL,
                storefront_id TEXT,
                binding_type TEXT NOT NULL,
                binding_status TEXT NOT NULL DEFAULT 'active',
                owner_type TEXT NOT NULL,
                partner_account_id TEXT,
                partner_code_id TEXT,
                reason_code TEXT,
                evidence_payload TEXT NOT NULL DEFAULT '{}',
                created_by_admin_user_id TEXT,
                effective_from TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                effective_to TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id),
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (partner_code_id) REFERENCES partner_codes(id),
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_customer_commercial_bindings_user_id ON customer_commercial_bindings(user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_customer_commercial_bindings_auth_realm_id ON customer_commercial_bindings(auth_realm_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_customer_commercial_bindings_storefront_id ON customer_commercial_bindings(storefront_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_customer_commercial_bindings_binding_type ON customer_commercial_bindings(binding_type)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_customer_commercial_bindings_binding_status "
            "ON customer_commercial_bindings(binding_status)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_customer_commercial_bindings_owner_type ON customer_commercial_bindings(owner_type)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_customer_commercial_bindings_partner_account_id "
            "ON customer_commercial_bindings(partner_account_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_customer_commercial_bindings_partner_code_id "
            "ON customer_commercial_bindings(partner_code_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_customer_commercial_bindings_created_by_admin_user_id "
            "ON customer_commercial_bindings(created_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_customer_commercial_bindings_effective_from "
            "ON customer_commercial_bindings(effective_from)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_customer_commercial_bindings_effective_to ON customer_commercial_bindings(effective_to)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE order_attribution_results (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL UNIQUE,
                user_id TEXT NOT NULL,
                auth_realm_id TEXT NOT NULL,
                storefront_id TEXT NOT NULL,
                owner_type TEXT NOT NULL,
                owner_source TEXT,
                partner_account_id TEXT,
                partner_code_id TEXT,
                winning_touchpoint_id TEXT,
                winning_binding_id TEXT,
                rule_path TEXT NOT NULL DEFAULT '[]',
                evidence_snapshot TEXT NOT NULL DEFAULT '{}',
                explainability_snapshot TEXT NOT NULL DEFAULT '{}',
                policy_snapshot TEXT NOT NULL DEFAULT '{}',
                resolved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id),
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (partner_code_id) REFERENCES partner_codes(id),
                FOREIGN KEY (winning_touchpoint_id) REFERENCES attribution_touchpoints(id),
                FOREIGN KEY (winning_binding_id) REFERENCES customer_commercial_bindings(id)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_order_attribution_results_order_id ON order_attribution_results(order_id)",
            "CREATE INDEX ix_order_attribution_results_user_id ON order_attribution_results(user_id)",
            "CREATE INDEX ix_order_attribution_results_auth_realm_id ON order_attribution_results(auth_realm_id)",
            "CREATE INDEX ix_order_attribution_results_storefront_id ON order_attribution_results(storefront_id)",
            "CREATE INDEX ix_order_attribution_results_owner_type ON order_attribution_results(owner_type)",
            "CREATE INDEX ix_order_attribution_results_owner_source ON order_attribution_results(owner_source)",
            "CREATE INDEX ix_order_attribution_results_partner_account_id "
            "ON order_attribution_results(partner_account_id)",
            "CREATE INDEX ix_order_attribution_results_partner_code_id ON order_attribution_results(partner_code_id)",
            "CREATE INDEX ix_order_attribution_results_winning_touchpoint_id "
            "ON order_attribution_results(winning_touchpoint_id)",
            "CREATE INDEX ix_order_attribution_results_winning_binding_id "
            "ON order_attribution_results(winning_binding_id)",
            "CREATE INDEX ix_order_attribution_results_resolved_at ON order_attribution_results(resolved_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE renewal_orders (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL UNIQUE,
                initial_order_id TEXT NOT NULL,
                prior_order_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                auth_realm_id TEXT NOT NULL,
                storefront_id TEXT NOT NULL,
                originating_attribution_result_id TEXT,
                winning_binding_id TEXT,
                renewal_sequence_number INTEGER NOT NULL DEFAULT 1,
                renewal_mode TEXT NOT NULL DEFAULT 'manual',
                provenance_owner_type TEXT NOT NULL DEFAULT 'none',
                provenance_owner_source TEXT,
                provenance_partner_account_id TEXT,
                provenance_partner_code_id TEXT,
                effective_owner_type TEXT NOT NULL DEFAULT 'none',
                effective_owner_source TEXT,
                effective_partner_account_id TEXT,
                effective_partner_code_id TEXT,
                payout_eligible INTEGER NOT NULL DEFAULT 0,
                payout_block_reason_codes TEXT NOT NULL DEFAULT '[]',
                lineage_snapshot TEXT NOT NULL DEFAULT '{}',
                explainability_snapshot TEXT NOT NULL DEFAULT '{}',
                policy_snapshot TEXT NOT NULL DEFAULT '{}',
                resolved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (initial_order_id) REFERENCES orders(id),
                FOREIGN KEY (prior_order_id) REFERENCES orders(id),
                FOREIGN KEY (user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id),
                FOREIGN KEY (originating_attribution_result_id) REFERENCES order_attribution_results(id),
                FOREIGN KEY (winning_binding_id) REFERENCES customer_commercial_bindings(id),
                FOREIGN KEY (provenance_partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (provenance_partner_code_id) REFERENCES partner_codes(id),
                FOREIGN KEY (effective_partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (effective_partner_code_id) REFERENCES partner_codes(id)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_renewal_orders_order_id ON renewal_orders(order_id)",
            "CREATE INDEX ix_renewal_orders_initial_order_id ON renewal_orders(initial_order_id)",
            "CREATE INDEX ix_renewal_orders_prior_order_id ON renewal_orders(prior_order_id)",
            "CREATE INDEX ix_renewal_orders_user_id ON renewal_orders(user_id)",
            "CREATE INDEX ix_renewal_orders_auth_realm_id ON renewal_orders(auth_realm_id)",
            "CREATE INDEX ix_renewal_orders_storefront_id ON renewal_orders(storefront_id)",
            "CREATE INDEX ix_renewal_orders_originating_attribution_result_id "
            "ON renewal_orders(originating_attribution_result_id)",
            "CREATE INDEX ix_renewal_orders_winning_binding_id ON renewal_orders(winning_binding_id)",
            "CREATE INDEX ix_renewal_orders_provenance_partner_account_id "
            "ON renewal_orders(provenance_partner_account_id)",
            "CREATE INDEX ix_renewal_orders_provenance_partner_code_id "
            "ON renewal_orders(provenance_partner_code_id)",
            "CREATE INDEX ix_renewal_orders_effective_partner_account_id "
            "ON renewal_orders(effective_partner_account_id)",
            "CREATE INDEX ix_renewal_orders_effective_partner_code_id "
            "ON renewal_orders(effective_partner_code_id)",
            "CREATE INDEX ix_renewal_orders_payout_eligible ON renewal_orders(payout_eligible)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE payments (
                id TEXT PRIMARY KEY,
                external_id TEXT,
                user_uuid TEXT NOT NULL,
                amount NUMERIC NOT NULL,
                currency TEXT NOT NULL,
                status TEXT NOT NULL,
                provider TEXT NOT NULL,
                subscription_days INTEGER NOT NULL,
                plan_id TEXT,
                promo_code_id TEXT,
                partner_code_id TEXT,
                discount_amount NUMERIC NOT NULL DEFAULT 0,
                wallet_amount_used NUMERIC NOT NULL DEFAULT 0,
                final_amount NUMERIC,
                addons_snapshot TEXT,
                entitlements_snapshot TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_payments_external_id ON payments(external_id)")
        conn.exec_driver_sql("CREATE INDEX ix_payments_user_uuid ON payments(user_uuid)")
        conn.exec_driver_sql("CREATE INDEX ix_payments_status ON payments(status)")
        conn.exec_driver_sql(
            """
            CREATE TABLE referral_commissions (
                id TEXT PRIMARY KEY,
                referrer_user_id TEXT NOT NULL,
                referred_user_id TEXT NOT NULL,
                payment_id TEXT NOT NULL,
                commission_rate NUMERIC NOT NULL,
                base_amount NUMERIC NOT NULL,
                commission_amount NUMERIC NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                wallet_tx_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_referral_commissions_referrer_user_id ON referral_commissions(referrer_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_referral_commissions_referred_user_id ON referral_commissions(referred_user_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE payment_attempts (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                payment_id TEXT UNIQUE,
                supersedes_attempt_id TEXT,
                attempt_number INTEGER NOT NULL DEFAULT 1,
                provider TEXT NOT NULL,
                sale_channel TEXT NOT NULL DEFAULT 'web',
                currency_code TEXT NOT NULL DEFAULT 'USD',
                status TEXT NOT NULL DEFAULT 'pending',
                displayed_amount NUMERIC NOT NULL,
                wallet_amount NUMERIC NOT NULL DEFAULT 0,
                gateway_amount NUMERIC NOT NULL DEFAULT 0,
                external_reference TEXT,
                idempotency_key TEXT NOT NULL,
                provider_snapshot TEXT NOT NULL DEFAULT '{}',
                request_snapshot TEXT NOT NULL DEFAULT '{}',
                terminal_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(order_id, idempotency_key),
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (payment_id) REFERENCES payments(id),
                FOREIGN KEY (supersedes_attempt_id) REFERENCES payment_attempts(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_payment_attempts_order_id ON payment_attempts(order_id)")
        conn.exec_driver_sql("CREATE INDEX ix_payment_attempts_payment_id ON payment_attempts(payment_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_payment_attempts_supersedes_attempt_id ON payment_attempts(supersedes_attempt_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_payment_attempts_status ON payment_attempts(status)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_payment_attempts_external_reference ON payment_attempts(external_reference)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_payment_attempts_idempotency_key ON payment_attempts(idempotency_key)")
        conn.exec_driver_sql(
            """
            CREATE TABLE refunds (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                payment_attempt_id TEXT,
                payment_id TEXT,
                refund_status TEXT NOT NULL DEFAULT 'requested',
                amount NUMERIC NOT NULL,
                currency_code TEXT NOT NULL DEFAULT 'USD',
                provider TEXT,
                reason_code TEXT,
                reason_text TEXT,
                external_reference TEXT,
                idempotency_key TEXT NOT NULL,
                provider_snapshot TEXT NOT NULL DEFAULT '{}',
                request_snapshot TEXT NOT NULL DEFAULT '{}',
                submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(order_id, idempotency_key),
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (payment_attempt_id) REFERENCES payment_attempts(id),
                FOREIGN KEY (payment_id) REFERENCES payments(id)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_refunds_order_id ON refunds(order_id)",
            "CREATE INDEX ix_refunds_payment_attempt_id ON refunds(payment_attempt_id)",
            "CREATE INDEX ix_refunds_payment_id ON refunds(payment_id)",
            "CREATE INDEX ix_refunds_refund_status ON refunds(refund_status)",
            "CREATE INDEX ix_refunds_provider ON refunds(provider)",
            "CREATE INDEX ix_refunds_reason_code ON refunds(reason_code)",
            "CREATE INDEX ix_refunds_external_reference ON refunds(external_reference)",
            "CREATE INDEX ix_refunds_idempotency_key ON refunds(idempotency_key)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE payment_disputes (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                payment_attempt_id TEXT,
                payment_id TEXT,
                provider TEXT,
                external_reference TEXT,
                subtype TEXT NOT NULL,
                outcome_class TEXT NOT NULL DEFAULT 'open',
                lifecycle_status TEXT NOT NULL DEFAULT 'opened',
                disputed_amount NUMERIC NOT NULL,
                fee_amount NUMERIC NOT NULL DEFAULT 0,
                fee_status TEXT NOT NULL DEFAULT 'none',
                currency_code TEXT NOT NULL DEFAULT 'USD',
                reason_code TEXT,
                evidence_snapshot TEXT NOT NULL DEFAULT '{}',
                provider_snapshot TEXT NOT NULL DEFAULT '{}',
                opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                closed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (payment_attempt_id) REFERENCES payment_attempts(id),
                FOREIGN KEY (payment_id) REFERENCES payments(id)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_payment_disputes_order_id ON payment_disputes(order_id)",
            "CREATE INDEX ix_payment_disputes_payment_attempt_id ON payment_disputes(payment_attempt_id)",
            "CREATE INDEX ix_payment_disputes_payment_id ON payment_disputes(payment_id)",
            "CREATE INDEX ix_payment_disputes_provider ON payment_disputes(provider)",
            "CREATE INDEX ix_payment_disputes_external_reference ON payment_disputes(external_reference)",
            "CREATE INDEX ix_payment_disputes_subtype ON payment_disputes(subtype)",
            "CREATE INDEX ix_payment_disputes_outcome_class ON payment_disputes(outcome_class)",
            "CREATE INDEX ix_payment_disputes_lifecycle_status ON payment_disputes(lifecycle_status)",
            "CREATE INDEX ix_payment_disputes_reason_code ON payment_disputes(reason_code)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE dispute_cases (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL,
                payment_dispute_id TEXT,
                order_id TEXT,
                case_kind TEXT NOT NULL,
                case_status TEXT NOT NULL DEFAULT 'open',
                summary TEXT NOT NULL,
                case_payload TEXT NOT NULL DEFAULT '{}',
                notes_payload TEXT NOT NULL DEFAULT '[]',
                opened_by_admin_user_id TEXT,
                assigned_to_admin_user_id TEXT,
                closed_by_admin_user_id TEXT,
                closed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (payment_dispute_id) REFERENCES payment_disputes(id) ON DELETE SET NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL,
                FOREIGN KEY (opened_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                FOREIGN KEY (assigned_to_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                FOREIGN KEY (closed_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_dispute_cases_partner_account_id ON dispute_cases(partner_account_id)",
            "CREATE INDEX ix_dispute_cases_payment_dispute_id ON dispute_cases(payment_dispute_id)",
            "CREATE INDEX ix_dispute_cases_order_id ON dispute_cases(order_id)",
            "CREATE INDEX ix_dispute_cases_case_kind ON dispute_cases(case_kind)",
            "CREATE INDEX ix_dispute_cases_case_status ON dispute_cases(case_status)",
            "CREATE INDEX ix_dispute_cases_opened_by_admin_user_id ON dispute_cases(opened_by_admin_user_id)",
            "CREATE INDEX ix_dispute_cases_assigned_to_admin_user_id ON dispute_cases(assigned_to_admin_user_id)",
            "CREATE INDEX ix_dispute_cases_closed_by_admin_user_id ON dispute_cases(closed_by_admin_user_id)",
            "CREATE INDEX ix_dispute_cases_closed_at ON dispute_cases(closed_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_workspace_workflow_events (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL,
                subject_kind TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                action_kind TEXT NOT NULL,
                message TEXT NOT NULL,
                event_payload TEXT NOT NULL DEFAULT '{}',
                created_by_admin_user_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            (
                "CREATE INDEX ix_partner_workspace_workflow_events_partner_account_id "
                "ON partner_workspace_workflow_events(partner_account_id)"
            ),
            (
                "CREATE INDEX ix_partner_workspace_workflow_events_subject_kind "
                "ON partner_workspace_workflow_events(subject_kind)"
            ),
            (
                "CREATE INDEX ix_partner_workspace_workflow_events_subject_id "
                "ON partner_workspace_workflow_events(subject_id)"
            ),
            (
                "CREATE INDEX ix_partner_workspace_workflow_events_action_kind "
                "ON partner_workspace_workflow_events(action_kind)"
            ),
            (
                "CREATE INDEX ix_partner_workspace_workflow_events_created_by_admin_user_id "
                "ON partner_workspace_workflow_events(created_by_admin_user_id)"
            ),
            (
                "CREATE INDEX ix_partner_workspace_workflow_events_created_at "
                "ON partner_workspace_workflow_events(created_at)"
            ),
            (
                "CREATE INDEX ix_partner_workspace_workflow_events_subject_scope "
                "ON partner_workspace_workflow_events("
                "partner_account_id, subject_kind, subject_id, created_at)"
            ),
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_workspace_profiles (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL UNIQUE,
                website TEXT,
                country TEXT,
                operating_regions TEXT,
                languages TEXT,
                contact_name TEXT,
                contact_email TEXT,
                support_contact TEXT,
                technical_contact TEXT,
                finance_contact TEXT,
                business_description TEXT,
                acquisition_channels TEXT,
                preferred_currency TEXT NOT NULL DEFAULT 'USD',
                require_mfa_for_workspace INTEGER NOT NULL DEFAULT 0,
                prefer_passkeys INTEGER NOT NULL DEFAULT 0,
                reviewed_active_sessions INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id) ON DELETE CASCADE
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_partner_workspace_profiles_partner_account_id "
            "ON partner_workspace_profiles(partner_account_id)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_workspace_legal_acceptances (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL,
                document_kind TEXT NOT NULL,
                document_version TEXT NOT NULL,
                accepted_by_admin_user_id TEXT,
                accepted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (accepted_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                UNIQUE (partner_account_id, document_kind, document_version)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_partner_workspace_legal_acceptances_partner_account_id "
            "ON partner_workspace_legal_acceptances(partner_account_id)",
            "CREATE INDEX ix_partner_workspace_legal_acceptances_document_kind "
            "ON partner_workspace_legal_acceptances(document_kind)",
            "CREATE INDEX ix_partner_workspace_legal_acceptances_accepted_by_admin_user_id "
            "ON partner_workspace_legal_acceptances(accepted_by_admin_user_id)",
            "CREATE INDEX ix_partner_workspace_legal_acceptances_accepted_at "
            "ON partner_workspace_legal_acceptances(accepted_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_application_drafts (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL UNIQUE,
                applicant_admin_user_id TEXT UNIQUE,
                draft_payload TEXT NOT NULL DEFAULT '{}',
                review_ready INTEGER NOT NULL DEFAULT 0,
                submitted_at TEXT,
                withdrawn_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (applicant_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_partner_application_drafts_partner_account_id "
            "ON partner_application_drafts(partner_account_id)",
            "CREATE INDEX ix_partner_application_drafts_applicant_admin_user_id "
            "ON partner_application_drafts(applicant_admin_user_id)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_lane_applications (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL,
                partner_application_draft_id TEXT NOT NULL,
                lane_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                application_payload TEXT NOT NULL DEFAULT '{}',
                submitted_at TEXT,
                decided_at TEXT,
                decision_reason_code TEXT,
                decision_summary TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (partner_application_draft_id) REFERENCES partner_application_drafts(id) ON DELETE CASCADE,
                UNIQUE (partner_account_id, lane_key)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_partner_lane_applications_partner_account_id "
            "ON partner_lane_applications(partner_account_id)",
            "CREATE INDEX ix_partner_lane_applications_partner_application_draft_id "
            "ON partner_lane_applications(partner_application_draft_id)",
            "CREATE INDEX ix_partner_lane_applications_lane_key ON partner_lane_applications(lane_key)",
            "CREATE INDEX ix_partner_lane_applications_status ON partner_lane_applications(status)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_application_review_requests (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL,
                partner_application_draft_id TEXT NOT NULL,
                lane_application_id TEXT,
                request_kind TEXT NOT NULL,
                message TEXT NOT NULL,
                required_fields TEXT NOT NULL DEFAULT '[]',
                required_attachments TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'open',
                requested_by_admin_user_id TEXT,
                resolved_by_admin_user_id TEXT,
                requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                response_due_at TEXT,
                responded_at TEXT,
                resolved_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (partner_application_draft_id) REFERENCES partner_application_drafts(id) ON DELETE CASCADE,
                FOREIGN KEY (lane_application_id) REFERENCES partner_lane_applications(id) ON DELETE SET NULL,
                FOREIGN KEY (requested_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                FOREIGN KEY (resolved_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_partner_application_review_requests_partner_account_id "
            "ON partner_application_review_requests(partner_account_id)",
            "CREATE INDEX ix_partner_application_review_requests_partner_application_draft_id "
            "ON partner_application_review_requests(partner_application_draft_id)",
            "CREATE INDEX ix_partner_application_review_requests_lane_application_id "
            "ON partner_application_review_requests(lane_application_id)",
            "CREATE INDEX ix_partner_application_review_requests_request_kind "
            "ON partner_application_review_requests(request_kind)",
            "CREATE INDEX ix_partner_application_review_requests_status "
            "ON partner_application_review_requests(status)",
            "CREATE INDEX ix_partner_application_review_requests_requested_by_admin_user_id "
            "ON partner_application_review_requests(requested_by_admin_user_id)",
            "CREATE INDEX ix_partner_application_review_requests_resolved_by_admin_user_id "
            "ON partner_application_review_requests(resolved_by_admin_user_id)",
            "CREATE INDEX ix_partner_application_review_requests_requested_at "
            "ON partner_application_review_requests(requested_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_application_attachments (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL,
                partner_application_draft_id TEXT NOT NULL,
                lane_application_id TEXT,
                review_request_id TEXT,
                attachment_type TEXT NOT NULL,
                storage_key TEXT NOT NULL UNIQUE,
                file_name TEXT,
                attachment_metadata TEXT NOT NULL DEFAULT '{}',
                uploaded_by_admin_user_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (partner_application_draft_id) REFERENCES partner_application_drafts(id) ON DELETE CASCADE,
                FOREIGN KEY (lane_application_id) REFERENCES partner_lane_applications(id) ON DELETE SET NULL,
                FOREIGN KEY (review_request_id) REFERENCES partner_application_review_requests(id) ON DELETE SET NULL,
                FOREIGN KEY (uploaded_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_partner_application_attachments_partner_account_id "
            "ON partner_application_attachments(partner_account_id)",
            "CREATE INDEX ix_partner_application_attachments_partner_application_draft_id "
            "ON partner_application_attachments(partner_application_draft_id)",
            "CREATE INDEX ix_partner_application_attachments_lane_application_id "
            "ON partner_application_attachments(lane_application_id)",
            "CREATE INDEX ix_partner_application_attachments_review_request_id "
            "ON partner_application_attachments(review_request_id)",
            "CREATE INDEX ix_partner_application_attachments_attachment_type "
            "ON partner_application_attachments(attachment_type)",
            "CREATE INDEX ix_partner_application_attachments_uploaded_by_admin_user_id "
            "ON partner_application_attachments(uploaded_by_admin_user_id)",
            "CREATE INDEX ix_partner_application_attachments_created_at "
            "ON partner_application_attachments(created_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_notification_read_states (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT NOT NULL,
                admin_user_id TEXT NOT NULL,
                notification_key TEXT NOT NULL,
                read_at TEXT,
                archived_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (admin_user_id) REFERENCES admin_users(id) ON DELETE CASCADE,
                UNIQUE (partner_account_id, admin_user_id, notification_key)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_partner_notification_read_states_partner_account_id "
            "ON partner_notification_read_states(partner_account_id)",
            "CREATE INDEX ix_partner_notification_read_states_admin_user_id "
            "ON partner_notification_read_states(admin_user_id)",
            "CREATE INDEX ix_partner_notification_read_states_notification_key "
            "ON partner_notification_read_states(notification_key)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE pilot_cohorts (
                id TEXT PRIMARY KEY,
                cohort_key TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                lane_key TEXT NOT NULL,
                surface_key TEXT NOT NULL,
                cohort_status TEXT NOT NULL DEFAULT 'scheduled',
                partner_account_id TEXT,
                owner_team TEXT NOT NULL,
                owner_admin_user_id TEXT NOT NULL,
                rollback_trigger_code TEXT NOT NULL,
                shadow_gate_payload TEXT NOT NULL DEFAULT '{}',
                monitoring_payload TEXT NOT NULL DEFAULT '{}',
                notes_payload TEXT NOT NULL DEFAULT '[]',
                scheduled_start_at TEXT NOT NULL,
                scheduled_end_at TEXT NOT NULL,
                activated_at TEXT,
                paused_at TEXT,
                completed_at TEXT,
                pause_reason_code TEXT,
                created_by_admin_user_id TEXT,
                activated_by_admin_user_id TEXT,
                paused_by_admin_user_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (owner_admin_user_id) REFERENCES admin_users(id) ON DELETE RESTRICT,
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                FOREIGN KEY (activated_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                FOREIGN KEY (paused_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_pilot_cohorts_cohort_key ON pilot_cohorts(cohort_key)",
            "CREATE INDEX ix_pilot_cohorts_lane_key ON pilot_cohorts(lane_key)",
            "CREATE INDEX ix_pilot_cohorts_surface_key ON pilot_cohorts(surface_key)",
            "CREATE INDEX ix_pilot_cohorts_cohort_status ON pilot_cohorts(cohort_status)",
            "CREATE INDEX ix_pilot_cohorts_partner_account_id ON pilot_cohorts(partner_account_id)",
            "CREATE INDEX ix_pilot_cohorts_owner_team ON pilot_cohorts(owner_team)",
            "CREATE INDEX ix_pilot_cohorts_owner_admin_user_id ON pilot_cohorts(owner_admin_user_id)",
            "CREATE INDEX ix_pilot_cohorts_scheduled_start_at ON pilot_cohorts(scheduled_start_at)",
            "CREATE INDEX ix_pilot_cohorts_scheduled_end_at ON pilot_cohorts(scheduled_end_at)",
            "CREATE INDEX ix_pilot_cohorts_activated_at ON pilot_cohorts(activated_at)",
            "CREATE INDEX ix_pilot_cohorts_paused_at ON pilot_cohorts(paused_at)",
            "CREATE INDEX ix_pilot_cohorts_completed_at ON pilot_cohorts(completed_at)",
            "CREATE INDEX ix_pilot_cohorts_created_by_admin_user_id ON pilot_cohorts(created_by_admin_user_id)",
            "CREATE INDEX ix_pilot_cohorts_activated_by_admin_user_id ON pilot_cohorts(activated_by_admin_user_id)",
            "CREATE INDEX ix_pilot_cohorts_paused_by_admin_user_id ON pilot_cohorts(paused_by_admin_user_id)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE pilot_rollout_windows (
                id TEXT PRIMARY KEY,
                pilot_cohort_id TEXT NOT NULL,
                window_kind TEXT NOT NULL,
                target_ref TEXT NOT NULL,
                window_status TEXT NOT NULL DEFAULT 'scheduled',
                starts_at TEXT NOT NULL,
                ends_at TEXT NOT NULL,
                notes_payload TEXT NOT NULL DEFAULT '[]',
                created_by_admin_user_id TEXT,
                closed_by_admin_user_id TEXT,
                closed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pilot_cohort_id) REFERENCES pilot_cohorts(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                FOREIGN KEY (closed_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_pilot_rollout_windows_pilot_cohort_id ON pilot_rollout_windows(pilot_cohort_id)",
            "CREATE INDEX ix_pilot_rollout_windows_window_kind ON pilot_rollout_windows(window_kind)",
            "CREATE INDEX ix_pilot_rollout_windows_target_ref ON pilot_rollout_windows(target_ref)",
            "CREATE INDEX ix_pilot_rollout_windows_window_status ON pilot_rollout_windows(window_status)",
            "CREATE INDEX ix_pilot_rollout_windows_starts_at ON pilot_rollout_windows(starts_at)",
            "CREATE INDEX ix_pilot_rollout_windows_ends_at ON pilot_rollout_windows(ends_at)",
            "CREATE INDEX ix_pilot_rollout_windows_created_by_admin_user_id "
            "ON pilot_rollout_windows(created_by_admin_user_id)",
            "CREATE INDEX ix_pilot_rollout_windows_closed_by_admin_user_id "
            "ON pilot_rollout_windows(closed_by_admin_user_id)",
            "CREATE INDEX ix_pilot_rollout_windows_closed_at ON pilot_rollout_windows(closed_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE pilot_owner_acknowledgements (
                id TEXT PRIMARY KEY,
                pilot_cohort_id TEXT NOT NULL,
                owner_team TEXT NOT NULL,
                acknowledgement_status TEXT NOT NULL DEFAULT 'acknowledged',
                runbook_reference TEXT NOT NULL,
                notes_payload TEXT NOT NULL DEFAULT '[]',
                acknowledged_by_admin_user_id TEXT,
                acknowledged_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pilot_cohort_id) REFERENCES pilot_cohorts(id) ON DELETE CASCADE,
                FOREIGN KEY (acknowledged_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_pilot_owner_acknowledgements_pilot_cohort_id "
            "ON pilot_owner_acknowledgements(pilot_cohort_id)",
            "CREATE INDEX ix_pilot_owner_acknowledgements_owner_team "
            "ON pilot_owner_acknowledgements(owner_team)",
            "CREATE INDEX ix_pilot_owner_acknowledgements_acknowledgement_status "
            "ON pilot_owner_acknowledgements(acknowledgement_status)",
            "CREATE INDEX ix_pilot_owner_acknowledgements_acknowledged_by_admin_user_id "
            "ON pilot_owner_acknowledgements(acknowledged_by_admin_user_id)",
            "CREATE INDEX ix_pilot_owner_acknowledgements_acknowledged_at "
            "ON pilot_owner_acknowledgements(acknowledged_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE pilot_rollback_drills (
                id TEXT PRIMARY KEY,
                pilot_cohort_id TEXT NOT NULL,
                cutover_unit_key TEXT NOT NULL,
                rollback_scope_class TEXT NOT NULL,
                trigger_code TEXT NOT NULL,
                drill_status TEXT NOT NULL,
                runbook_reference TEXT NOT NULL,
                observed_metric_payload TEXT NOT NULL DEFAULT '{}',
                notes_payload TEXT NOT NULL DEFAULT '[]',
                executed_by_admin_user_id TEXT,
                executed_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pilot_cohort_id) REFERENCES pilot_cohorts(id) ON DELETE CASCADE,
                FOREIGN KEY (executed_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_pilot_rollback_drills_pilot_cohort_id ON pilot_rollback_drills(pilot_cohort_id)",
            "CREATE INDEX ix_pilot_rollback_drills_cutover_unit_key ON pilot_rollback_drills(cutover_unit_key)",
            "CREATE INDEX ix_pilot_rollback_drills_rollback_scope_class "
            "ON pilot_rollback_drills(rollback_scope_class)",
            "CREATE INDEX ix_pilot_rollback_drills_drill_status ON pilot_rollback_drills(drill_status)",
            "CREATE INDEX ix_pilot_rollback_drills_executed_by_admin_user_id "
            "ON pilot_rollback_drills(executed_by_admin_user_id)",
            "CREATE INDEX ix_pilot_rollback_drills_executed_at ON pilot_rollback_drills(executed_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE pilot_go_no_go_decisions (
                id TEXT PRIMARY KEY,
                pilot_cohort_id TEXT NOT NULL,
                decision_status TEXT NOT NULL,
                decision_reason_code TEXT,
                release_ring TEXT NOT NULL DEFAULT 'R3',
                rollback_scope_class TEXT NOT NULL,
                cutover_unit_keys_payload TEXT NOT NULL DEFAULT '[]',
                evidence_links_payload TEXT NOT NULL DEFAULT '[]',
                acknowledged_owner_teams_payload TEXT NOT NULL DEFAULT '[]',
                monitoring_snapshot_payload TEXT NOT NULL DEFAULT '{}',
                notes_payload TEXT NOT NULL DEFAULT '[]',
                decided_by_admin_user_id TEXT,
                decided_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pilot_cohort_id) REFERENCES pilot_cohorts(id) ON DELETE CASCADE,
                FOREIGN KEY (decided_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_pilot_go_no_go_decisions_pilot_cohort_id "
            "ON pilot_go_no_go_decisions(pilot_cohort_id)",
            "CREATE INDEX ix_pilot_go_no_go_decisions_decision_status "
            "ON pilot_go_no_go_decisions(decision_status)",
            "CREATE INDEX ix_pilot_go_no_go_decisions_rollback_scope_class "
            "ON pilot_go_no_go_decisions(rollback_scope_class)",
            "CREATE INDEX ix_pilot_go_no_go_decisions_decided_by_admin_user_id "
            "ON pilot_go_no_go_decisions(decided_by_admin_user_id)",
            "CREATE INDEX ix_pilot_go_no_go_decisions_decided_at "
            "ON pilot_go_no_go_decisions(decided_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE commissionability_evaluations (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL UNIQUE,
                commissionability_status TEXT NOT NULL DEFAULT 'pending',
                reason_codes TEXT NOT NULL DEFAULT '[]',
                partner_context_present INTEGER NOT NULL DEFAULT 0,
                program_allows_commissionability INTEGER NOT NULL DEFAULT 0,
                positive_commission_base INTEGER NOT NULL DEFAULT 0,
                paid_status INTEGER NOT NULL DEFAULT 0,
                fully_refunded INTEGER NOT NULL DEFAULT 0,
                open_payment_dispute_present INTEGER NOT NULL DEFAULT 0,
                risk_allowed INTEGER NOT NULL DEFAULT 1,
                evaluation_snapshot TEXT NOT NULL DEFAULT '{}',
                explainability_snapshot TEXT NOT NULL DEFAULT '{}',
                evaluated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_commissionability_evaluations_order_id ON commissionability_evaluations(order_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_commissionability_evaluations_commissionability_status "
            "ON commissionability_evaluations(commissionability_status)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE growth_reward_allocations (
                id TEXT PRIMARY KEY,
                reward_type TEXT NOT NULL,
                allocation_status TEXT NOT NULL DEFAULT 'allocated',
                beneficiary_user_id TEXT NOT NULL,
                auth_realm_id TEXT NOT NULL,
                storefront_id TEXT,
                order_id TEXT,
                invite_code_id TEXT,
                referral_commission_id TEXT,
                source_key TEXT UNIQUE,
                quantity NUMERIC NOT NULL DEFAULT 1,
                unit TEXT NOT NULL,
                currency_code TEXT,
                reward_payload TEXT NOT NULL DEFAULT '{}',
                created_by_admin_user_id TEXT,
                allocated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reversed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_growth_reward_allocations_reward_type ON growth_reward_allocations(reward_type)",
            "CREATE INDEX ix_growth_reward_allocations_allocation_status "
            "ON growth_reward_allocations(allocation_status)",
            "CREATE INDEX ix_growth_reward_allocations_beneficiary_user_id "
            "ON growth_reward_allocations(beneficiary_user_id)",
            "CREATE INDEX ix_growth_reward_allocations_auth_realm_id ON growth_reward_allocations(auth_realm_id)",
            "CREATE INDEX ix_growth_reward_allocations_storefront_id ON growth_reward_allocations(storefront_id)",
            "CREATE INDEX ix_growth_reward_allocations_order_id ON growth_reward_allocations(order_id)",
            "CREATE INDEX ix_growth_reward_allocations_invite_code_id ON growth_reward_allocations(invite_code_id)",
            "CREATE INDEX ix_growth_reward_allocations_referral_commission_id "
            "ON growth_reward_allocations(referral_commission_id)",
            "CREATE INDEX ix_growth_reward_allocations_created_by_admin_user_id "
            "ON growth_reward_allocations(created_by_admin_user_id)",
            "CREATE INDEX ix_growth_reward_allocations_allocated_at ON growth_reward_allocations(allocated_at)",
            "CREATE INDEX ix_growth_reward_allocations_reversed_at ON growth_reward_allocations(reversed_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE service_identities (
                id TEXT PRIMARY KEY,
                service_key TEXT NOT NULL UNIQUE,
                customer_account_id TEXT NOT NULL,
                auth_realm_id TEXT NOT NULL,
                source_order_id TEXT,
                origin_storefront_id TEXT,
                provider_name TEXT NOT NULL,
                provider_subject_ref TEXT,
                identity_status TEXT NOT NULL DEFAULT 'active',
                service_context TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_account_id) REFERENCES mobile_users(id),
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (source_order_id) REFERENCES orders(id),
                FOREIGN KEY (origin_storefront_id) REFERENCES storefronts(id),
                UNIQUE (customer_account_id, auth_realm_id, provider_name)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_service_identities_service_key ON service_identities(service_key)",
            "CREATE INDEX ix_service_identities_customer_account_id ON service_identities(customer_account_id)",
            "CREATE INDEX ix_service_identities_auth_realm_id ON service_identities(auth_realm_id)",
            "CREATE INDEX ix_service_identities_source_order_id ON service_identities(source_order_id)",
            "CREATE INDEX ix_service_identities_origin_storefront_id ON service_identities(origin_storefront_id)",
            "CREATE INDEX ix_service_identities_provider_name ON service_identities(provider_name)",
            "CREATE INDEX ix_service_identities_provider_subject_ref ON service_identities(provider_subject_ref)",
            "CREATE INDEX ix_service_identities_identity_status ON service_identities(identity_status)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE provisioning_profiles (
                id TEXT PRIMARY KEY,
                service_identity_id TEXT NOT NULL,
                profile_key TEXT NOT NULL,
                target_channel TEXT NOT NULL,
                delivery_method TEXT NOT NULL,
                profile_status TEXT NOT NULL DEFAULT 'active',
                provider_name TEXT NOT NULL,
                provider_profile_ref TEXT,
                provisioning_payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (service_identity_id) REFERENCES service_identities(id),
                UNIQUE (service_identity_id, profile_key)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_provisioning_profiles_service_identity_id ON provisioning_profiles(service_identity_id)",
            "CREATE INDEX ix_provisioning_profiles_profile_key ON provisioning_profiles(profile_key)",
            "CREATE INDEX ix_provisioning_profiles_target_channel ON provisioning_profiles(target_channel)",
            "CREATE INDEX ix_provisioning_profiles_delivery_method ON provisioning_profiles(delivery_method)",
            "CREATE INDEX ix_provisioning_profiles_profile_status ON provisioning_profiles(profile_status)",
            "CREATE INDEX ix_provisioning_profiles_provider_name ON provisioning_profiles(provider_name)",
            "CREATE INDEX ix_provisioning_profiles_provider_profile_ref ON provisioning_profiles(provider_profile_ref)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE entitlement_grants (
                id TEXT PRIMARY KEY,
                grant_key TEXT NOT NULL UNIQUE,
                service_identity_id TEXT NOT NULL,
                customer_account_id TEXT NOT NULL,
                auth_realm_id TEXT NOT NULL,
                origin_storefront_id TEXT,
                source_type TEXT NOT NULL,
                source_order_id TEXT UNIQUE,
                source_growth_reward_allocation_id TEXT UNIQUE,
                source_renewal_order_id TEXT UNIQUE,
                manual_source_key TEXT UNIQUE,
                grant_status TEXT NOT NULL DEFAULT 'pending',
                grant_snapshot TEXT NOT NULL DEFAULT '{}',
                source_snapshot TEXT NOT NULL DEFAULT '{}',
                effective_from TEXT,
                expires_at TEXT,
                created_by_admin_user_id TEXT,
                activated_at TEXT,
                activated_by_admin_user_id TEXT,
                suspended_at TEXT,
                suspended_by_admin_user_id TEXT,
                suspension_reason_code TEXT,
                revoked_at TEXT,
                revoked_by_admin_user_id TEXT,
                revoke_reason_code TEXT,
                expired_at TEXT,
                expired_by_admin_user_id TEXT,
                expiry_reason_code TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (service_identity_id) REFERENCES service_identities(id),
                FOREIGN KEY (customer_account_id) REFERENCES mobile_users(id),
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (origin_storefront_id) REFERENCES storefronts(id),
                FOREIGN KEY (source_order_id) REFERENCES orders(id),
                FOREIGN KEY (source_growth_reward_allocation_id) REFERENCES growth_reward_allocations(id),
                FOREIGN KEY (source_renewal_order_id) REFERENCES renewal_orders(id),
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (activated_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (suspended_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (revoked_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (expired_by_admin_user_id) REFERENCES admin_users(id)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_entitlement_grants_grant_key ON entitlement_grants(grant_key)",
            "CREATE INDEX ix_entitlement_grants_service_identity_id ON entitlement_grants(service_identity_id)",
            "CREATE INDEX ix_entitlement_grants_customer_account_id ON entitlement_grants(customer_account_id)",
            "CREATE INDEX ix_entitlement_grants_auth_realm_id ON entitlement_grants(auth_realm_id)",
            "CREATE INDEX ix_entitlement_grants_origin_storefront_id ON entitlement_grants(origin_storefront_id)",
            "CREATE INDEX ix_entitlement_grants_source_type ON entitlement_grants(source_type)",
            "CREATE INDEX ix_entitlement_grants_source_order_id ON entitlement_grants(source_order_id)",
            "CREATE INDEX ix_entitlement_grants_source_growth_reward_allocation_id "
            "ON entitlement_grants(source_growth_reward_allocation_id)",
            "CREATE INDEX ix_entitlement_grants_source_renewal_order_id ON entitlement_grants(source_renewal_order_id)",
            "CREATE INDEX ix_entitlement_grants_manual_source_key ON entitlement_grants(manual_source_key)",
            "CREATE INDEX ix_entitlement_grants_grant_status ON entitlement_grants(grant_status)",
            "CREATE INDEX ix_entitlement_grants_effective_from ON entitlement_grants(effective_from)",
            "CREATE INDEX ix_entitlement_grants_expires_at ON entitlement_grants(expires_at)",
            "CREATE INDEX ix_entitlement_grants_created_by_admin_user_id "
            "ON entitlement_grants(created_by_admin_user_id)",
            "CREATE INDEX ix_entitlement_grants_activated_at ON entitlement_grants(activated_at)",
            "CREATE INDEX ix_entitlement_grants_activated_by_admin_user_id "
            "ON entitlement_grants(activated_by_admin_user_id)",
            "CREATE INDEX ix_entitlement_grants_suspended_at ON entitlement_grants(suspended_at)",
            "CREATE INDEX ix_entitlement_grants_suspended_by_admin_user_id "
            "ON entitlement_grants(suspended_by_admin_user_id)",
            "CREATE INDEX ix_entitlement_grants_revoked_at ON entitlement_grants(revoked_at)",
            "CREATE INDEX ix_entitlement_grants_revoked_by_admin_user_id "
            "ON entitlement_grants(revoked_by_admin_user_id)",
            "CREATE INDEX ix_entitlement_grants_expired_at ON entitlement_grants(expired_at)",
            "CREATE INDEX ix_entitlement_grants_expired_by_admin_user_id "
            "ON entitlement_grants(expired_by_admin_user_id)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE device_credentials (
                id TEXT PRIMARY KEY,
                credential_key TEXT NOT NULL UNIQUE,
                service_identity_id TEXT NOT NULL,
                auth_realm_id TEXT NOT NULL,
                origin_storefront_id TEXT,
                provisioning_profile_id TEXT,
                credential_type TEXT NOT NULL,
                credential_status TEXT NOT NULL DEFAULT 'active',
                subject_key TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                provider_credential_ref TEXT,
                credential_context TEXT NOT NULL DEFAULT '{}',
                issued_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_used_at TEXT,
                revoked_at TEXT,
                revoked_by_admin_user_id TEXT,
                revoke_reason_code TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (service_identity_id) REFERENCES service_identities(id),
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (origin_storefront_id) REFERENCES storefronts(id),
                FOREIGN KEY (provisioning_profile_id) REFERENCES provisioning_profiles(id),
                FOREIGN KEY (revoked_by_admin_user_id) REFERENCES admin_users(id),
                UNIQUE (service_identity_id, credential_type, subject_key)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_device_credentials_credential_key ON device_credentials(credential_key)",
            "CREATE INDEX ix_device_credentials_service_identity_id ON device_credentials(service_identity_id)",
            "CREATE INDEX ix_device_credentials_auth_realm_id ON device_credentials(auth_realm_id)",
            "CREATE INDEX ix_device_credentials_origin_storefront_id ON device_credentials(origin_storefront_id)",
            "CREATE INDEX ix_device_credentials_provisioning_profile_id ON device_credentials(provisioning_profile_id)",
            "CREATE INDEX ix_device_credentials_credential_type ON device_credentials(credential_type)",
            "CREATE INDEX ix_device_credentials_credential_status ON device_credentials(credential_status)",
            "CREATE INDEX ix_device_credentials_subject_key ON device_credentials(subject_key)",
            "CREATE INDEX ix_device_credentials_provider_name ON device_credentials(provider_name)",
            "CREATE INDEX ix_device_credentials_provider_credential_ref "
            "ON device_credentials(provider_credential_ref)",
            "CREATE INDEX ix_device_credentials_issued_at ON device_credentials(issued_at)",
            "CREATE INDEX ix_device_credentials_last_used_at ON device_credentials(last_used_at)",
            "CREATE INDEX ix_device_credentials_revoked_at ON device_credentials(revoked_at)",
            "CREATE INDEX ix_device_credentials_revoked_by_admin_user_id "
            "ON device_credentials(revoked_by_admin_user_id)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE access_delivery_channels (
                id TEXT PRIMARY KEY,
                delivery_key TEXT NOT NULL UNIQUE,
                service_identity_id TEXT NOT NULL,
                auth_realm_id TEXT NOT NULL,
                origin_storefront_id TEXT,
                provisioning_profile_id TEXT,
                device_credential_id TEXT,
                channel_type TEXT NOT NULL,
                channel_status TEXT NOT NULL DEFAULT 'active',
                channel_subject_ref TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                delivery_context TEXT NOT NULL DEFAULT '{}',
                delivery_payload TEXT NOT NULL DEFAULT '{}',
                last_delivered_at TEXT,
                last_accessed_at TEXT,
                archived_at TEXT,
                archived_by_admin_user_id TEXT,
                archive_reason_code TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (service_identity_id) REFERENCES service_identities(id),
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (origin_storefront_id) REFERENCES storefronts(id),
                FOREIGN KEY (provisioning_profile_id) REFERENCES provisioning_profiles(id),
                FOREIGN KEY (device_credential_id) REFERENCES device_credentials(id),
                FOREIGN KEY (archived_by_admin_user_id) REFERENCES admin_users(id),
                UNIQUE (service_identity_id, channel_type, channel_subject_ref)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_access_delivery_channels_delivery_key ON access_delivery_channels(delivery_key)",
            "CREATE INDEX ix_access_delivery_channels_service_identity_id "
            "ON access_delivery_channels(service_identity_id)",
            "CREATE INDEX ix_access_delivery_channels_auth_realm_id ON access_delivery_channels(auth_realm_id)",
            "CREATE INDEX ix_access_delivery_channels_origin_storefront_id "
            "ON access_delivery_channels(origin_storefront_id)",
            "CREATE INDEX ix_access_delivery_channels_provisioning_profile_id "
            "ON access_delivery_channels(provisioning_profile_id)",
            "CREATE INDEX ix_access_delivery_channels_device_credential_id "
            "ON access_delivery_channels(device_credential_id)",
            "CREATE INDEX ix_access_delivery_channels_channel_type ON access_delivery_channels(channel_type)",
            "CREATE INDEX ix_access_delivery_channels_channel_status ON access_delivery_channels(channel_status)",
            "CREATE INDEX ix_access_delivery_channels_channel_subject_ref "
            "ON access_delivery_channels(channel_subject_ref)",
            "CREATE INDEX ix_access_delivery_channels_provider_name ON access_delivery_channels(provider_name)",
            "CREATE INDEX ix_access_delivery_channels_last_delivered_at "
            "ON access_delivery_channels(last_delivered_at)",
            "CREATE INDEX ix_access_delivery_channels_last_accessed_at "
            "ON access_delivery_channels(last_accessed_at)",
            "CREATE INDEX ix_access_delivery_channels_archived_at ON access_delivery_channels(archived_at)",
            "CREATE INDEX ix_access_delivery_channels_archived_by_admin_user_id "
            "ON access_delivery_channels(archived_by_admin_user_id)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE outbox_events (
                id TEXT PRIMARY KEY,
                event_key TEXT NOT NULL UNIQUE,
                event_name TEXT NOT NULL,
                event_family TEXT NOT NULL,
                aggregate_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                partition_key TEXT NOT NULL,
                schema_version INTEGER NOT NULL DEFAULT 1,
                event_status TEXT NOT NULL DEFAULT 'pending_publication',
                event_payload TEXT NOT NULL DEFAULT '{}',
                actor_context TEXT NOT NULL DEFAULT '{}',
                source_context TEXT NOT NULL DEFAULT '{}',
                occurred_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_outbox_events_event_name ON outbox_events(event_name)",
            "CREATE INDEX ix_outbox_events_event_family ON outbox_events(event_family)",
            "CREATE INDEX ix_outbox_events_aggregate_type ON outbox_events(aggregate_type)",
            "CREATE INDEX ix_outbox_events_aggregate_id ON outbox_events(aggregate_id)",
            "CREATE INDEX ix_outbox_events_partition_key ON outbox_events(partition_key)",
            "CREATE INDEX ix_outbox_events_event_status ON outbox_events(event_status)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE outbox_publications (
                id TEXT PRIMARY KEY,
                outbox_event_id TEXT NOT NULL,
                consumer_key TEXT NOT NULL,
                publication_status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                lease_owner TEXT,
                leased_until TEXT,
                next_attempt_at TEXT NOT NULL,
                submitted_at TEXT,
                published_at TEXT,
                last_error TEXT,
                publication_payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (outbox_event_id) REFERENCES outbox_events(id) ON DELETE CASCADE,
                UNIQUE (outbox_event_id, consumer_key)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_outbox_publications_outbox_event_id ON outbox_publications(outbox_event_id)",
            "CREATE INDEX ix_outbox_publications_consumer_key ON outbox_publications(consumer_key)",
            "CREATE INDEX ix_outbox_publications_publication_status "
            "ON outbox_publications(publication_status)",
            "CREATE INDEX ix_outbox_publications_lease_owner ON outbox_publications(lease_owner)",
            "CREATE INDEX ix_outbox_publications_leased_until ON outbox_publications(leased_until)",
        ):
            conn.exec_driver_sql(index_sql)


@asynccontextmanager
async def override_realm_test_db(sessionmaker: sessionmaker[Session]) -> AsyncGenerator[None]:
    async def _override_db() -> AsyncGenerator[SyncSessionAdapter]:
        with sessionmaker() as session:
            adapter = SyncSessionAdapter(session)
            try:
                yield adapter
                session.commit()
            except Exception:
                session.rollback()
                raise

    from src.main import app

    app.dependency_overrides[get_db] = _override_db
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)


def cleanup_sqlite_file(path: Path) -> None:
    path.unlink(missing_ok=True)
