from __future__ import annotations

from collections import defaultdict
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from http.cookies import SimpleCookie
from pathlib import Path
from tempfile import NamedTemporaryFile

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.infrastructure.cache.passkey_fresh_auth import PasskeyFreshAuthGrantStore
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.passkey_fresh_auth import FRESH_AUTH_GRANT_ID_HEADER

ADMIN_AUTH_REALM_HEADERS = {
    "Host": "testserver",
    "X-Forwarded-Host": "admin.cyber-vpn.net",
    "X-Auth-Realm": "admin",
}
ADMIN_ACCESS_COOKIE_NAME = "access_token"

PARTNER_AUTH_REALM_HEADERS = {
    "Host": "testserver",
    "X-Forwarded-Host": "portal.localhost",
    "X-Auth-Realm": "partner",
}
PARTNER_ACCESS_COOKIE_NAME = "partner_access_token"
_REALM_TEST_ENGINES: dict[Path, object] = {}


def access_token_from_client_cookies(client, *, cookie_name: str = ADMIN_ACCESS_COOKIE_NAME, response=None) -> str:
    access_token = response.cookies.get(cookie_name) if response is not None else None
    if access_token is None and response is not None:
        for header in response.headers.get_list("set-cookie"):
            parsed = SimpleCookie()
            parsed.load(header)
            if cookie_name in parsed:
                access_token = parsed[cookie_name].value
                break
    if access_token is None:
        access_token = client.cookies.get(cookie_name)
    assert access_token is not None
    return access_token


async def fresh_auth_headers(
    *,
    fake_redis: FakeRedis,
    base_headers: dict[str, str],
    user,
    auth_realm_id,
    realm_key: str,
    action: str,
    principal_class: str,
) -> dict[str, str]:
    grant = await PasskeyFreshAuthGrantStore(fake_redis).create(
        principal_subject=str(user.id),
        principal_class=principal_class,
        auth_realm_id=str(auth_realm_id),
        realm_key=realm_key,
        action=action,
        ttl_seconds=300,
    )
    return {**base_headers, FRESH_AUTH_GRANT_ID_HEADER: grant.grant_id}


class _FakeRedisPipeline:
    def __init__(self, sorted_sets: dict[str, dict[str, float]], expiry: dict[str, int]) -> None:
        self._sorted_sets = sorted_sets
        self._expiry = expiry
        self._ops: list[tuple[str, tuple]] = []

    async def __aenter__(self) -> _FakeRedisPipeline:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def zremrangebyscore(self, key: str, minimum: float, maximum: float) -> None:
        self._ops.append(("zremrangebyscore", (key, minimum, maximum)))

    def zadd(self, key: str, mapping: dict[str, float]) -> None:
        self._ops.append(("zadd", (key, mapping)))

    def zcard(self, key: str) -> None:
        self._ops.append(("zcard", (key,)))

    def expire(self, key: str, seconds: int) -> None:
        self._ops.append(("expire", (key, seconds)))

    async def execute(self) -> list[int | bool]:
        results: list[int | bool] = []
        for op_name, args in self._ops:
            if op_name == "zremrangebyscore":
                key, minimum, maximum = args
                bucket = self._sorted_sets[key]
                removed = [
                    member for member, score in bucket.items() if float(minimum) <= float(score) <= float(maximum)
                ]
                for member in removed:
                    bucket.pop(member, None)
                results.append(len(removed))
            elif op_name == "zadd":
                key, mapping = args
                self._sorted_sets[key].update({str(member): float(score) for member, score in mapping.items()})
                results.append(len(mapping))
            elif op_name == "zcard":
                (key,) = args
                results.append(len(self._sorted_sets[key]))
            elif op_name == "expire":
                key, seconds = args
                self._expiry[key] = int(seconds)
                results.append(True)
        return results


class FakeRedis:
    def __init__(self) -> None:
        self._values: dict[str, object] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._sorted_sets: dict[str, dict[str, float]] = defaultdict(dict)
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

    async def getdel(self, key: str) -> object | None:
        value = self._values.pop(key, None)
        self._expiry.pop(key, None)
        return value

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

    def pipeline(self, transaction: bool = True) -> _FakeRedisPipeline:
        _ = transaction
        return _FakeRedisPipeline(self._sorted_sets, self._expiry)


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

    @asynccontextmanager
    async def begin_nested(self):
        with self._session.begin_nested():
            yield self


def create_realm_test_sessionmaker() -> tuple[sessionmaker[Session], object, Path]:
    temp_file = NamedTemporaryFile(prefix="cybervpn-realm-auth-", suffix=".sqlite3", delete=False)
    temp_file.close()
    sqlite_path = Path(temp_file.name)
    engine = create_engine(f"sqlite:///{sqlite_path}", future=True)
    factory = sessionmaker(engine, class_=Session, expire_on_commit=False)
    _REALM_TEST_ENGINES[sqlite_path] = engine
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
            "CREATE INDEX ix_merchant_profiles_invoice_profile_id ON merchant_profiles(invoice_profile_id)"
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
                catalog_access_class TEXT NOT NULL DEFAULT 'admin_only',
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
            "CREATE INDEX ix_offer_versions_subscription_plan_id ON offer_versions(subscription_plan_id)"
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
            CREATE TABLE audit_logs (
                id TEXT PRIMARY KEY,
                admin_id TEXT,
                action TEXT NOT NULL,
                entity_type TEXT,
                entity_id TEXT,
                old_value TEXT,
                new_value TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_audit_logs_admin_id ON audit_logs(admin_id)")
        conn.exec_driver_sql("CREATE INDEX ix_audit_logs_action ON audit_logs(action)")
        conn.exec_driver_sql("CREATE INDEX ix_audit_logs_entity_type ON audit_logs(entity_type)")
        conn.exec_driver_sql("CREATE INDEX ix_audit_logs_created_at ON audit_logs(created_at)")
        conn.exec_driver_sql(
            """
            CREATE TABLE refresh_tokens (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                auth_realm_id TEXT NOT NULL,
                principal_class TEXT NOT NULL CHECK (principal_class IN ('admin', 'partner_operator', 'customer')),
                principal_subject TEXT NOT NULL CHECK (principal_subject <> ''),
                audience TEXT NOT NULL CHECK (audience <> ''),
                scope_family TEXT NOT NULL CHECK (scope_family <> ''),
                token_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                revoked_at TEXT,
                revoked_reason TEXT,
                jti TEXT,
                family_id TEXT,
                parent_token_id TEXT,
                principal_session_id TEXT,
                consumed_at TEXT,
                replaced_by_token_id TEXT,
                device_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                last_used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (parent_token_id) REFERENCES refresh_tokens(id),
                FOREIGN KEY (principal_session_id) REFERENCES principal_sessions(id),
                FOREIGN KEY (replaced_by_token_id) REFERENCES refresh_tokens(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens(user_id)")
        conn.exec_driver_sql("CREATE INDEX ix_refresh_tokens_auth_realm_id ON refresh_tokens(auth_realm_id)")
        conn.exec_driver_sql("CREATE INDEX ix_refresh_tokens_principal_class ON refresh_tokens(principal_class)")
        conn.exec_driver_sql("CREATE INDEX ix_refresh_tokens_principal_subject ON refresh_tokens(principal_subject)")
        conn.exec_driver_sql("CREATE INDEX ix_refresh_tokens_audience ON refresh_tokens(audience)")
        conn.exec_driver_sql("CREATE INDEX ix_refresh_tokens_scope_family ON refresh_tokens(scope_family)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_refresh_tokens_principal_owner "
            "ON refresh_tokens(principal_class, principal_subject, auth_realm_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_refresh_tokens_token_hash ON refresh_tokens(token_hash)")
        conn.exec_driver_sql("CREATE UNIQUE INDEX uq_refresh_tokens_jti ON refresh_tokens(jti)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_refresh_tokens_principal_session_id ON refresh_tokens(principal_session_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_refresh_tokens_family_id ON refresh_tokens(family_id)")
        conn.exec_driver_sql("CREATE INDEX ix_refresh_tokens_parent_token_id ON refresh_tokens(parent_token_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_refresh_tokens_replaced_by_token_id ON refresh_tokens(replaced_by_token_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_refresh_tokens_consumed_at ON refresh_tokens(consumed_at)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_refresh_tokens_session_family ON refresh_tokens(principal_session_id, family_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE passkey_credentials (
                id TEXT PRIMARY KEY,
                credential_id TEXT NOT NULL,
                credential_id_hash TEXT NOT NULL UNIQUE,
                credential_public_key BLOB NOT NULL,
                sign_count INTEGER NOT NULL DEFAULT 0,
                auth_realm_id TEXT NOT NULL,
                realm_key TEXT NOT NULL,
                audience TEXT NOT NULL,
                principal_class TEXT NOT NULL,
                principal_subject TEXT NOT NULL,
                user_handle TEXT NOT NULL,
                label TEXT NOT NULL,
                surface TEXT NOT NULL,
                rp_id TEXT NOT NULL,
                origin TEXT,
                aaguid TEXT,
                attestation_format TEXT,
                credential_type TEXT NOT NULL DEFAULT 'public-key',
                device_type TEXT,
                transports TEXT NOT NULL DEFAULT '[]',
                backed_up INTEGER NOT NULL DEFAULT 0,
                user_verified INTEGER NOT NULL DEFAULT 0,
                authenticator_attachment TEXT,
                policy_snapshot TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'active',
                clone_suspected_at TEXT,
                last_used_at TEXT,
                revoked_at TEXT,
                deleted_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_passkey_credentials_auth_realm_id ON passkey_credentials(auth_realm_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_passkey_credentials_credential_id_hash ON passkey_credentials(credential_id_hash)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_passkey_credentials_principal_class ON passkey_credentials(principal_class)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_passkey_credentials_principal_subject ON passkey_credentials(principal_subject)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_passkey_credentials_realm_key ON passkey_credentials(realm_key)")
        conn.exec_driver_sql("CREATE INDEX ix_passkey_credentials_status ON passkey_credentials(status)")
        conn.exec_driver_sql("CREATE INDEX ix_passkey_credentials_user_handle ON passkey_credentials(user_handle)")
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
                public_uid INTEGER NOT NULL,
                auth_realm_id TEXT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                username TEXT UNIQUE,
                telegram_subject TEXT UNIQUE,
                telegram_id INTEGER UNIQUE,
                telegram_username TEXT,
                notification_prefs TEXT NOT NULL DEFAULT '{}',
                totp_secret TEXT,
                totp_enabled INTEGER NOT NULL DEFAULT 0,
                remnawave_uuid TEXT UNIQUE,
                subscription_url TEXT,
                referral_code TEXT UNIQUE,
                referred_by_user_id TEXT,
                referral_claimed_at TEXT,
                referral_source_code_id TEXT,
                referral_attribution_session_id TEXT,
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
                FOREIGN KEY (referral_source_code_id) REFERENCES growth_codes(id),
                FOREIGN KEY (referral_attribution_session_id) REFERENCES referral_attribution_sessions(id),
                FOREIGN KEY (partner_user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE UNIQUE INDEX ix_mobile_users_public_uid ON mobile_users(public_uid)")
        conn.exec_driver_sql("CREATE INDEX ix_mobile_users_auth_realm_id ON mobile_users(auth_realm_id)")
        conn.exec_driver_sql("CREATE INDEX ix_mobile_users_referred_by_user_id ON mobile_users(referred_by_user_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_mobile_users_referral_source_code_id ON mobile_users(referral_source_code_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_mobile_users_referral_attribution_session_id "
            "ON mobile_users(referral_attribution_session_id)"
        )
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
            CREATE TABLE notification_queue (
                id TEXT PRIMARY KEY,
                telegram_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                notification_type TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                scheduled_at TEXT NOT NULL,
                sent_at TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_notification_queue_status_scheduled ON notification_queue(status, scheduled_at)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE growth_code_benefits (
                id TEXT PRIMARY KEY,
                growth_code_id TEXT NOT NULL,
                policy_version_id TEXT,
                benefit_type TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                merge_mode TEXT NOT NULL DEFAULT 'append',
                config TEXT NOT NULL DEFAULT '{}',
                eligibility TEXT NOT NULL DEFAULT '{}',
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (growth_code_id) REFERENCES growth_codes(id) ON DELETE CASCADE,
                FOREIGN KEY (policy_version_id) REFERENCES policy_versions(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_growth_code_benefits_growth_code_id ON growth_code_benefits(growth_code_id)",
            "CREATE INDEX ix_growth_code_benefits_policy_version_id ON growth_code_benefits(policy_version_id)",
            "CREATE INDEX ix_growth_code_benefits_benefit_type ON growth_code_benefits(benefit_type)",
            "CREATE INDEX ix_growth_code_benefits_trigger_type ON growth_code_benefits(trigger_type)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE growth_benefit_fulfillments (
                id TEXT PRIMARY KEY,
                benefit_id TEXT NOT NULL,
                growth_code_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                order_id TEXT NOT NULL,
                payment_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                config_snapshot TEXT NOT NULL DEFAULT '{}',
                result_payload TEXT NOT NULL DEFAULT '{}',
                error_code TEXT,
                error_message TEXT,
                started_at TEXT,
                completed_at TEXT,
                next_retry_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (benefit_id) REFERENCES growth_code_benefits(id) ON DELETE RESTRICT,
                FOREIGN KEY (growth_code_id) REFERENCES growth_codes(id) ON DELETE RESTRICT,
                FOREIGN KEY (user_id) REFERENCES mobile_users(id) ON DELETE RESTRICT,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE RESTRICT,
                FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE RESTRICT,
                CHECK (attempt_count >= 0)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_growth_benefit_fulfillments_benefit_id ON growth_benefit_fulfillments(benefit_id)",
            "CREATE INDEX ix_growth_benefit_fulfillments_growth_code_id ON growth_benefit_fulfillments(growth_code_id)",
            "CREATE INDEX ix_growth_benefit_fulfillments_user_id ON growth_benefit_fulfillments(user_id)",
            "CREATE INDEX ix_growth_benefit_fulfillments_order_id ON growth_benefit_fulfillments(order_id)",
            "CREATE INDEX ix_growth_benefit_fulfillments_payment_id ON growth_benefit_fulfillments(payment_id)",
            "CREATE INDEX ix_growth_benefit_fulfillments_idempotency_key "
            "ON growth_benefit_fulfillments(idempotency_key)",
            "CREATE INDEX ix_growth_benefit_fulfillments_status ON growth_benefit_fulfillments(status)",
            "CREATE INDEX ix_growth_benefit_fulfillments_next_retry_at ON growth_benefit_fulfillments(next_retry_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE invite_batches (
                id TEXT PRIMARY KEY,
                owner_user_id TEXT NOT NULL,
                campaign_id TEXT,
                source_growth_code_id TEXT,
                source_benefit_id TEXT,
                source_order_id TEXT,
                source_payment_id TEXT,
                source_type TEXT NOT NULL,
                requested_count INTEGER NOT NULL,
                issued_count INTEGER NOT NULL DEFAULT 0,
                friend_days INTEGER NOT NULL,
                expiry_mode TEXT NOT NULL,
                expiry_days INTEGER,
                expires_at TEXT,
                entitlement_mode TEXT NOT NULL,
                entitlement_profile_key TEXT,
                plan_id TEXT,
                entitlement_snapshot TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                revoked_at TEXT,
                revoked_by_admin_id TEXT,
                revoked_reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_user_id) REFERENCES mobile_users(id) ON DELETE RESTRICT,
                FOREIGN KEY (source_growth_code_id) REFERENCES growth_codes(id) ON DELETE SET NULL,
                FOREIGN KEY (source_benefit_id) REFERENCES growth_code_benefits(id) ON DELETE SET NULL,
                FOREIGN KEY (source_order_id) REFERENCES orders(id) ON DELETE SET NULL,
                FOREIGN KEY (source_payment_id) REFERENCES payments(id) ON DELETE SET NULL,
                FOREIGN KEY (plan_id) REFERENCES subscription_plans(id) ON DELETE SET NULL,
                CHECK (requested_count > 0),
                CHECK (issued_count >= 0),
                CHECK (issued_count <= requested_count),
                CHECK (friend_days > 0),
                CHECK (expiry_mode IN ('none', 'relative', 'absolute'))
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_invite_batches_owner_user_id ON invite_batches(owner_user_id)",
            "CREATE INDEX ix_invite_batches_campaign_id ON invite_batches(campaign_id)",
            "CREATE INDEX ix_invite_batches_source_growth_code_id ON invite_batches(source_growth_code_id)",
            "CREATE INDEX ix_invite_batches_source_benefit_id ON invite_batches(source_benefit_id)",
            "CREATE INDEX ix_invite_batches_source_order_id ON invite_batches(source_order_id)",
            "CREATE INDEX ix_invite_batches_source_payment_id ON invite_batches(source_payment_id)",
            "CREATE INDEX ix_invite_batches_source_type ON invite_batches(source_type)",
            "CREATE INDEX ix_invite_batches_plan_id ON invite_batches(plan_id)",
            "CREATE INDEX ix_invite_batches_status ON invite_batches(status)",
            "CREATE INDEX ix_invite_batches_idempotency_key ON invite_batches(idempotency_key)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE invite_codes (
                id TEXT PRIMARY KEY,
                code TEXT NOT NULL UNIQUE,
                owner_user_id TEXT NOT NULL,
                free_days INTEGER NOT NULL,
                plan_id TEXT,
                batch_id TEXT,
                source_growth_code_id TEXT,
                source_benefit_id TEXT,
                status TEXT NOT NULL DEFAULT 'issued',
                code_hash TEXT,
                code_prefix TEXT,
                entitlement_mode TEXT,
                entitlement_profile_key TEXT,
                entitlement_snapshot TEXT NOT NULL DEFAULT '{}',
                source TEXT NOT NULL,
                source_payment_id TEXT,
                is_used INTEGER NOT NULL DEFAULT 0,
                used_by_user_id TEXT,
                used_at TEXT,
                revoked_at TEXT,
                revoked_by_admin_id TEXT,
                revoked_reason TEXT,
                expires_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_invite_codes_code ON invite_codes(code)")
        conn.exec_driver_sql("CREATE INDEX ix_invite_codes_owner_user_id ON invite_codes(owner_user_id)")
        conn.exec_driver_sql("CREATE INDEX ix_invite_codes_batch_id ON invite_codes(batch_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_invite_codes_source_growth_code_id ON invite_codes(source_growth_code_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_invite_codes_source_benefit_id ON invite_codes(source_benefit_id)")
        conn.exec_driver_sql("CREATE INDEX ix_invite_codes_status ON invite_codes(status)")
        conn.exec_driver_sql("CREATE INDEX ix_invite_codes_code_hash ON invite_codes(code_hash)")
        conn.exec_driver_sql("CREATE INDEX ix_invite_codes_code_prefix ON invite_codes(code_prefix)")
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
            CREATE TABLE growth_codes (
                id TEXT PRIMARY KEY,
                code_hash TEXT NOT NULL,
                code_prefix TEXT NOT NULL,
                code_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                issuer_type TEXT NOT NULL,
                issuer_admin_id TEXT,
                owner_user_id TEXT,
                owner_partner_account_id TEXT,
                campaign_id TEXT,
                batch_id TEXT,
                storefront_id TEXT,
                auth_realm_id TEXT,
                policy_version_id TEXT,
                starts_at TEXT,
                expires_at TEXT,
                max_uses INTEGER,
                uses_count INTEGER NOT NULL DEFAULT 0,
                reserved_uses INTEGER NOT NULL DEFAULT 0,
                last_used_at TEXT,
                code_namespace TEXT NOT NULL DEFAULT 'customer_input',
                revoked_at TEXT,
                revoked_by_admin_id TEXT,
                revoked_reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (issuer_admin_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                FOREIGN KEY (owner_user_id) REFERENCES mobile_users(id) ON DELETE SET NULL,
                FOREIGN KEY (owner_partner_account_id) REFERENCES partner_accounts(id) ON DELETE SET NULL,
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id) ON DELETE SET NULL,
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id) ON DELETE SET NULL,
                FOREIGN KEY (policy_version_id) REFERENCES policy_versions(id) ON DELETE SET NULL,
                FOREIGN KEY (revoked_by_admin_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                UNIQUE (code_hash, code_type),
                UNIQUE (code_namespace, code_hash)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_growth_codes_code_hash ON growth_codes(code_hash)",
            "CREATE INDEX ix_growth_codes_code_prefix ON growth_codes(code_prefix)",
            "CREATE INDEX ix_growth_codes_code_type ON growth_codes(code_type)",
            "CREATE INDEX ix_growth_codes_status ON growth_codes(status)",
            "CREATE INDEX ix_growth_codes_issuer_type ON growth_codes(issuer_type)",
            "CREATE INDEX ix_growth_codes_issuer_admin_id ON growth_codes(issuer_admin_id)",
            "CREATE INDEX ix_growth_codes_owner_user_id ON growth_codes(owner_user_id)",
            "CREATE INDEX ix_growth_codes_owner_partner_account_id ON growth_codes(owner_partner_account_id)",
            "CREATE INDEX ix_growth_codes_campaign_id ON growth_codes(campaign_id)",
            "CREATE INDEX ix_growth_codes_batch_id ON growth_codes(batch_id)",
            "CREATE INDEX ix_growth_codes_storefront_id ON growth_codes(storefront_id)",
            "CREATE INDEX ix_growth_codes_auth_realm_id ON growth_codes(auth_realm_id)",
            "CREATE INDEX ix_growth_codes_policy_version_id ON growth_codes(policy_version_id)",
            "CREATE INDEX ix_growth_codes_starts_at ON growth_codes(starts_at)",
            "CREATE INDEX ix_growth_codes_expires_at ON growth_codes(expires_at)",
            "CREATE INDEX ix_growth_codes_last_used_at ON growth_codes(last_used_at)",
            "CREATE INDEX ix_growth_codes_code_namespace ON growth_codes(code_namespace)",
            "CREATE INDEX ix_growth_codes_revoked_at ON growth_codes(revoked_at)",
            "CREATE INDEX ix_growth_codes_revoked_by_admin_id ON growth_codes(revoked_by_admin_id)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE growth_code_issuances (
                id TEXT PRIMARY KEY,
                growth_code_id TEXT NOT NULL,
                issuance_type TEXT NOT NULL,
                issued_to_user_id TEXT,
                issued_to_partner_account_id TEXT,
                issued_by_admin_id TEXT,
                source_order_id TEXT,
                source_payment_id TEXT,
                source_plan_sku TEXT,
                raw_code_encrypted TEXT,
                source_bundle_snapshot TEXT NOT NULL DEFAULT '{}',
                reason_code TEXT,
                admin_note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (growth_code_id) REFERENCES growth_codes(id) ON DELETE CASCADE,
                FOREIGN KEY (issued_to_user_id) REFERENCES mobile_users(id) ON DELETE SET NULL,
                FOREIGN KEY (issued_to_partner_account_id) REFERENCES partner_accounts(id) ON DELETE SET NULL,
                FOREIGN KEY (issued_by_admin_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                FOREIGN KEY (source_order_id) REFERENCES orders(id) ON DELETE SET NULL,
                FOREIGN KEY (source_payment_id) REFERENCES payments(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_growth_code_issuances_growth_code_id ON growth_code_issuances(growth_code_id)",
            "CREATE INDEX ix_growth_code_issuances_issuance_type ON growth_code_issuances(issuance_type)",
            "CREATE INDEX ix_growth_code_issuances_issued_to_user_id ON growth_code_issuances(issued_to_user_id)",
            "CREATE INDEX ix_growth_code_issuances_issued_to_partner_account_id "
            "ON growth_code_issuances(issued_to_partner_account_id)",
            "CREATE INDEX ix_growth_code_issuances_issued_by_admin_id ON growth_code_issuances(issued_by_admin_id)",
            "CREATE INDEX ix_growth_code_issuances_source_order_id ON growth_code_issuances(source_order_id)",
            "CREATE INDEX ix_growth_code_issuances_source_payment_id ON growth_code_issuances(source_payment_id)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE growth_code_touchpoints (
                id TEXT PRIMARY KEY,
                growth_code_id TEXT NOT NULL,
                code_type TEXT NOT NULL,
                anonymous_session_id TEXT,
                registered_user_id TEXT,
                risk_subject_id TEXT,
                storefront_id TEXT,
                auth_realm_id TEXT,
                surface TEXT,
                channel TEXT,
                utm_source TEXT,
                utm_medium TEXT,
                utm_campaign TEXT,
                click_id TEXT,
                sub_id TEXT,
                ip_hash TEXT,
                user_agent_hash TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                converted_to_signup_at TEXT,
                converted_to_order_id TEXT,
                FOREIGN KEY (growth_code_id) REFERENCES growth_codes(id) ON DELETE CASCADE,
                FOREIGN KEY (registered_user_id) REFERENCES mobile_users(id) ON DELETE SET NULL,
                FOREIGN KEY (risk_subject_id) REFERENCES risk_subjects(id) ON DELETE SET NULL,
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id) ON DELETE SET NULL,
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id) ON DELETE SET NULL,
                FOREIGN KEY (converted_to_order_id) REFERENCES orders(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_growth_code_touchpoints_growth_code_id ON growth_code_touchpoints(growth_code_id)",
            "CREATE INDEX ix_growth_code_touchpoints_code_type ON growth_code_touchpoints(code_type)",
            "CREATE INDEX ix_growth_code_touchpoints_anonymous_session_id "
            "ON growth_code_touchpoints(anonymous_session_id)",
            "CREATE INDEX ix_growth_code_touchpoints_registered_user_id ON growth_code_touchpoints(registered_user_id)",
            "CREATE INDEX ix_growth_code_touchpoints_risk_subject_id ON growth_code_touchpoints(risk_subject_id)",
            "CREATE INDEX ix_growth_code_touchpoints_storefront_id ON growth_code_touchpoints(storefront_id)",
            "CREATE INDEX ix_growth_code_touchpoints_auth_realm_id ON growth_code_touchpoints(auth_realm_id)",
            "CREATE INDEX ix_growth_code_touchpoints_surface ON growth_code_touchpoints(surface)",
            "CREATE INDEX ix_growth_code_touchpoints_channel ON growth_code_touchpoints(channel)",
            "CREATE INDEX ix_growth_code_touchpoints_converted_to_signup_at "
            "ON growth_code_touchpoints(converted_to_signup_at)",
            "CREATE INDEX ix_growth_code_touchpoints_converted_to_order_id "
            "ON growth_code_touchpoints(converted_to_order_id)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE referral_attribution_sessions (
                id TEXT PRIMARY KEY,
                token_hash TEXT NOT NULL UNIQUE,
                growth_code_id TEXT NOT NULL,
                growth_code_touchpoint_id TEXT,
                referrer_user_id TEXT NOT NULL,
                claimed_by_user_id TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                source_host TEXT,
                source_path TEXT,
                campaign_params TEXT NOT NULL DEFAULT '{}',
                evidence_payload TEXT NOT NULL DEFAULT '{}',
                first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL,
                claimed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (growth_code_id) REFERENCES growth_codes(id) ON DELETE CASCADE,
                FOREIGN KEY (growth_code_touchpoint_id) REFERENCES growth_code_touchpoints(id) ON DELETE SET NULL,
                FOREIGN KEY (referrer_user_id) REFERENCES mobile_users(id) ON DELETE CASCADE,
                FOREIGN KEY (claimed_by_user_id) REFERENCES mobile_users(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_referral_attr_sessions_token_hash ON referral_attribution_sessions(token_hash)",
            "CREATE INDEX ix_referral_attr_sessions_growth_code_id ON referral_attribution_sessions(growth_code_id)",
            "CREATE INDEX ix_referral_attr_sessions_growth_touchpoint_id "
            "ON referral_attribution_sessions(growth_code_touchpoint_id)",
            "CREATE INDEX ix_referral_attr_sessions_referrer_user_id "
            "ON referral_attribution_sessions(referrer_user_id)",
            "CREATE INDEX ix_referral_attr_sessions_claimed_by_user_id "
            "ON referral_attribution_sessions(claimed_by_user_id)",
            "CREATE INDEX ix_referral_attr_sessions_status ON referral_attribution_sessions(status)",
            "CREATE INDEX ix_referral_attr_sessions_first_seen_at ON referral_attribution_sessions(first_seen_at)",
            "CREATE INDEX ix_referral_attr_sessions_expires_at ON referral_attribution_sessions(expires_at)",
            "CREATE INDEX ix_referral_attr_sessions_claimed_at ON referral_attribution_sessions(claimed_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE growth_signup_attributions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                growth_code_id TEXT NOT NULL,
                code_type TEXT NOT NULL,
                touchpoint_id TEXT NOT NULL,
                attribution_source TEXT NOT NULL,
                storefront_id TEXT,
                auth_realm_id TEXT,
                risk_subject_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES mobile_users(id) ON DELETE CASCADE,
                FOREIGN KEY (growth_code_id) REFERENCES growth_codes(id) ON DELETE CASCADE,
                FOREIGN KEY (touchpoint_id) REFERENCES growth_code_touchpoints(id) ON DELETE CASCADE,
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id) ON DELETE SET NULL,
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id) ON DELETE SET NULL,
                FOREIGN KEY (risk_subject_id) REFERENCES risk_subjects(id) ON DELETE SET NULL,
                UNIQUE (user_id)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_growth_signup_attributions_user_id ON growth_signup_attributions(user_id)",
            "CREATE INDEX ix_growth_signup_attributions_growth_code_id ON growth_signup_attributions(growth_code_id)",
            "CREATE INDEX ix_growth_signup_attributions_code_type ON growth_signup_attributions(code_type)",
            "CREATE INDEX ix_growth_signup_attributions_touchpoint_id ON growth_signup_attributions(touchpoint_id)",
            "CREATE INDEX ix_growth_signup_attributions_attribution_source "
            "ON growth_signup_attributions(attribution_source)",
            "CREATE INDEX ix_growth_signup_attributions_storefront_id ON growth_signup_attributions(storefront_id)",
            "CREATE INDEX ix_growth_signup_attributions_auth_realm_id ON growth_signup_attributions(auth_realm_id)",
            "CREATE INDEX ix_growth_signup_attributions_risk_subject_id ON growth_signup_attributions(risk_subject_id)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE invite_code_policies (
                id TEXT PRIMARY KEY,
                growth_code_id TEXT NOT NULL UNIQUE,
                friend_days INTEGER NOT NULL,
                entitlement_profile_key TEXT,
                conversion_reward_policy_id TEXT,
                self_redemption_block INTEGER NOT NULL DEFAULT 1,
                risk_ruleset_id TEXT,
                policy_snapshot TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (growth_code_id) REFERENCES growth_codes(id) ON DELETE CASCADE,
                FOREIGN KEY (conversion_reward_policy_id) REFERENCES policy_versions(id) ON DELETE SET NULL
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_invite_code_policies_growth_code_id ON invite_code_policies(growth_code_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_invite_code_policies_conversion_reward_policy_id "
            "ON invite_code_policies(conversion_reward_policy_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_invite_code_policies_risk_ruleset_id ON invite_code_policies(risk_ruleset_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE referral_program_policies (
                id TEXT PRIMARY KEY,
                growth_code_id TEXT UNIQUE,
                program_key TEXT UNIQUE,
                friend_discount_type TEXT,
                friend_discount_value NUMERIC,
                eligible_durations TEXT NOT NULL DEFAULT '[]',
                eligible_plan_families TEXT NOT NULL DEFAULT '[]',
                reward_type TEXT,
                reward_value NUMERIC,
                hold_days INTEGER,
                monthly_cap NUMERIC,
                lifetime_cap NUMERIC,
                anti_abuse_policy_id TEXT,
                policy_snapshot TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (growth_code_id) REFERENCES growth_codes(id) ON DELETE CASCADE,
                FOREIGN KEY (anti_abuse_policy_id) REFERENCES policy_versions(id) ON DELETE SET NULL
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_referral_program_policies_growth_code_id ON referral_program_policies(growth_code_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_referral_program_policies_program_key ON referral_program_policies(program_key)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_referral_program_policies_anti_abuse_policy_id "
            "ON referral_program_policies(anti_abuse_policy_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE promo_code_policies (
                id TEXT PRIMARY KEY,
                growth_code_id TEXT NOT NULL UNIQUE,
                discount_type TEXT NOT NULL,
                discount_value NUMERIC NOT NULL,
                max_discount_amount NUMERIC,
                eligible_plan_ids TEXT NOT NULL DEFAULT '[]',
                eligible_plan_families TEXT NOT NULL DEFAULT '[]',
                eligible_durations TEXT NOT NULL DEFAULT '[]',
                eligible_addons TEXT NOT NULL DEFAULT '[]',
                allowed_checkout_modes TEXT NOT NULL DEFAULT '[]',
                allowed_channels TEXT NOT NULL DEFAULT '[]',
                allowed_geos TEXT NOT NULL DEFAULT '[]',
                min_net_paid_amount NUMERIC,
                currency_code TEXT,
                discount_scope TEXT NOT NULL DEFAULT 'order',
                discountable_addon_codes TEXT NOT NULL DEFAULT '[]',
                minimum_order_amount NUMERIC,
                allow_zero_amount_order INTEGER NOT NULL DEFAULT 0,
                new_customer_only INTEGER NOT NULL DEFAULT 0,
                first_completed_order_only INTEGER NOT NULL DEFAULT 0,
                first_net_paid_order_only INTEGER NOT NULL DEFAULT 0,
                require_no_active_access INTEGER NOT NULL DEFAULT 0,
                commission_basis TEXT NOT NULL DEFAULT 'net_gateway_paid',
                include_wallet_in_commission_base INTEGER NOT NULL DEFAULT 0,
                policy_version INTEGER NOT NULL DEFAULT 1,
                is_current INTEGER NOT NULL DEFAULT 1,
                published_at TEXT,
                usage_cap_per_user INTEGER,
                global_usage_cap INTEGER,
                policy_snapshot TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (growth_code_id) REFERENCES growth_codes(id) ON DELETE CASCADE
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_promo_code_policies_growth_code_id ON promo_code_policies(growth_code_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE gift_code_policies (
                id TEXT PRIMARY KEY,
                growth_code_id TEXT NOT NULL UNIQUE,
                grant_type TEXT NOT NULL,
                plan_family TEXT,
                duration_days INTEGER,
                entitlement_snapshot TEXT NOT NULL DEFAULT '{}',
                redemption_mode TEXT,
                transferable INTEGER NOT NULL DEFAULT 0,
                batch_id TEXT,
                policy_snapshot TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (growth_code_id) REFERENCES growth_codes(id) ON DELETE CASCADE
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_gift_code_policies_growth_code_id ON gift_code_policies(growth_code_id)")
        conn.exec_driver_sql("CREATE INDEX ix_gift_code_policies_batch_id ON gift_code_policies(batch_id)")
        conn.exec_driver_sql(
            """
            CREATE TABLE growth_code_resolution_events (
                id TEXT PRIMARY KEY,
                growth_code_id TEXT,
                raw_code_hash TEXT NOT NULL,
                code_type TEXT,
                user_id TEXT,
                anonymous_session_id TEXT,
                checkout_session_id TEXT,
                order_id TEXT,
                surface TEXT NOT NULL DEFAULT 'api',
                action_context TEXT NOT NULL,
                result TEXT NOT NULL,
                reject_reason TEXT,
                conflict_code TEXT,
                policy_version_id TEXT,
                risk_decision_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (growth_code_id) REFERENCES growth_codes(id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES mobile_users(id) ON DELETE SET NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL,
                FOREIGN KEY (policy_version_id) REFERENCES policy_versions(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_growth_code_resolution_events_growth_code_id "
            "ON growth_code_resolution_events(growth_code_id)",
            "CREATE INDEX ix_growth_code_resolution_events_raw_code_hash "
            "ON growth_code_resolution_events(raw_code_hash)",
            "CREATE INDEX ix_growth_code_resolution_events_code_type ON growth_code_resolution_events(code_type)",
            "CREATE INDEX ix_growth_code_resolution_events_user_id ON growth_code_resolution_events(user_id)",
            "CREATE INDEX ix_growth_code_resolution_events_anonymous_session_id "
            "ON growth_code_resolution_events(anonymous_session_id)",
            "CREATE INDEX ix_growth_code_resolution_events_checkout_session_id "
            "ON growth_code_resolution_events(checkout_session_id)",
            "CREATE INDEX ix_growth_code_resolution_events_order_id ON growth_code_resolution_events(order_id)",
            "CREATE INDEX ix_growth_code_resolution_events_surface ON growth_code_resolution_events(surface)",
            "CREATE INDEX ix_growth_code_resolution_events_action_context "
            "ON growth_code_resolution_events(action_context)",
            "CREATE INDEX ix_growth_code_resolution_events_result ON growth_code_resolution_events(result)",
            "CREATE INDEX ix_growth_code_resolution_events_reject_reason "
            "ON growth_code_resolution_events(reject_reason)",
            "CREATE INDEX ix_growth_code_resolution_events_policy_version_id "
            "ON growth_code_resolution_events(policy_version_id)",
            "CREATE INDEX ix_growth_code_resolution_events_risk_decision_id "
            "ON growth_code_resolution_events(risk_decision_id)",
            "CREATE INDEX ix_growth_code_resolution_events_created_at ON growth_code_resolution_events(created_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE growth_code_reservations (
                id TEXT PRIMARY KEY,
                growth_code_id TEXT NOT NULL,
                quote_session_id TEXT,
                checkout_session_id TEXT,
                reservation_group_id TEXT,
                user_id TEXT,
                reserved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'reserved',
                consumed_order_id TEXT,
                committed_at TEXT,
                consumed_at TEXT,
                consumed_payment_id TEXT,
                released_at TEXT,
                release_reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (growth_code_id) REFERENCES growth_codes(id) ON DELETE CASCADE,
                FOREIGN KEY (quote_session_id) REFERENCES quote_sessions(id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES mobile_users(id) ON DELETE SET NULL,
                FOREIGN KEY (consumed_order_id) REFERENCES orders(id) ON DELETE SET NULL,
                FOREIGN KEY (consumed_payment_id) REFERENCES payments(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_growth_code_reservations_growth_code_id ON growth_code_reservations(growth_code_id)",
            "CREATE INDEX ix_growth_code_reservations_quote_session_id ON growth_code_reservations(quote_session_id)",
            "CREATE INDEX ix_growth_code_reservations_checkout_session_id "
            "ON growth_code_reservations(checkout_session_id)",
            "CREATE INDEX ix_growth_code_reservations_reservation_group_id "
            "ON growth_code_reservations(reservation_group_id)",
            "CREATE INDEX ix_growth_code_reservations_user_id ON growth_code_reservations(user_id)",
            "CREATE INDEX ix_growth_code_reservations_reserved_at ON growth_code_reservations(reserved_at)",
            "CREATE INDEX ix_growth_code_reservations_expires_at ON growth_code_reservations(expires_at)",
            "CREATE INDEX ix_growth_code_reservations_status ON growth_code_reservations(status)",
            "CREATE INDEX ix_growth_code_reservations_consumed_order_id ON growth_code_reservations(consumed_order_id)",
            "CREATE INDEX ix_growth_code_reservations_committed_at ON growth_code_reservations(committed_at)",
            "CREATE INDEX ix_growth_code_reservations_consumed_at ON growth_code_reservations(consumed_at)",
            "CREATE INDEX ix_growth_code_reservations_consumed_payment_id "
            "ON growth_code_reservations(consumed_payment_id)",
            "CREATE INDEX ix_growth_code_reservations_released_at ON growth_code_reservations(released_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE growth_code_redemptions (
                id TEXT PRIMARY KEY,
                growth_code_id TEXT NOT NULL,
                code_type TEXT NOT NULL,
                redeemer_user_id TEXT,
                beneficiary_user_id TEXT,
                order_id TEXT,
                payment_id TEXT,
                reservation_id TEXT,
                usage_number INTEGER,
                entitlement_grant_id TEXT,
                wallet_transaction_id TEXT,
                reward_allocation_id TEXT,
                policy_version_id TEXT,
                risk_decision_id TEXT,
                status TEXT NOT NULL DEFAULT 'redeemed',
                redeemed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reversed_at TEXT,
                reversal_reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (growth_code_id) REFERENCES growth_codes(id) ON DELETE CASCADE,
                FOREIGN KEY (redeemer_user_id) REFERENCES mobile_users(id) ON DELETE SET NULL,
                FOREIGN KEY (beneficiary_user_id) REFERENCES mobile_users(id) ON DELETE SET NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL,
                FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE SET NULL,
                FOREIGN KEY (reservation_id) REFERENCES growth_code_reservations(id) ON DELETE SET NULL,
                FOREIGN KEY (entitlement_grant_id) REFERENCES entitlement_grants(id) ON DELETE SET NULL,
                FOREIGN KEY (wallet_transaction_id) REFERENCES wallet_transactions(id) ON DELETE SET NULL,
                FOREIGN KEY (policy_version_id) REFERENCES policy_versions(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_growth_code_redemptions_growth_code_id ON growth_code_redemptions(growth_code_id)",
            "CREATE INDEX ix_growth_code_redemptions_code_type ON growth_code_redemptions(code_type)",
            "CREATE INDEX ix_growth_code_redemptions_redeemer_user_id ON growth_code_redemptions(redeemer_user_id)",
            "CREATE INDEX ix_growth_code_redemptions_beneficiary_user_id "
            "ON growth_code_redemptions(beneficiary_user_id)",
            "CREATE INDEX ix_growth_code_redemptions_order_id ON growth_code_redemptions(order_id)",
            "CREATE INDEX ix_growth_code_redemptions_payment_id ON growth_code_redemptions(payment_id)",
            "CREATE INDEX ix_growth_code_redemptions_reservation_id ON growth_code_redemptions(reservation_id)",
            "CREATE INDEX ix_growth_code_redemptions_entitlement_grant_id "
            "ON growth_code_redemptions(entitlement_grant_id)",
            "CREATE INDEX ix_growth_code_redemptions_wallet_transaction_id "
            "ON growth_code_redemptions(wallet_transaction_id)",
            "CREATE INDEX ix_growth_code_redemptions_reward_allocation_id "
            "ON growth_code_redemptions(reward_allocation_id)",
            "CREATE INDEX ix_growth_code_redemptions_policy_version_id ON growth_code_redemptions(policy_version_id)",
            "CREATE INDEX ix_growth_code_redemptions_risk_decision_id ON growth_code_redemptions(risk_decision_id)",
            "CREATE INDEX ix_growth_code_redemptions_status ON growth_code_redemptions(status)",
            "CREATE INDEX ix_growth_code_redemptions_redeemed_at ON growth_code_redemptions(redeemed_at)",
            "CREATE INDEX ix_growth_code_redemptions_reversed_at ON growth_code_redemptions(reversed_at)",
        ):
            conn.exec_driver_sql(index_sql)
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
                registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
            CREATE TABLE partner_commission_contracts (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT,
                partner_user_id TEXT,
                partner_code_id TEXT,
                owner_type TEXT NOT NULL DEFAULT 'affiliate',
                contract_status TEXT NOT NULL DEFAULT 'active',
                commission_model TEXT NOT NULL DEFAULT 'base_plus_markup',
                commission_pct NUMERIC NOT NULL DEFAULT 0,
                markup_pct NUMERIC NOT NULL DEFAULT 0,
                markup_cap_amount NUMERIC,
                payout_hold_days INTEGER NOT NULL DEFAULT 30,
                currency_code TEXT NOT NULL DEFAULT 'USD',
                currency_policy TEXT NOT NULL DEFAULT '{"minor_unit":2}',
                rounding_mode TEXT NOT NULL DEFAULT 'ROUND_HALF_UP',
                renewal_policy TEXT NOT NULL DEFAULT '{}',
                refund_policy TEXT NOT NULL DEFAULT '{}',
                terms_snapshot TEXT NOT NULL DEFAULT '{}',
                source TEXT NOT NULL DEFAULT 'runtime_code_create',
                version INTEGER NOT NULL DEFAULT 1,
                effective_from TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                effective_to TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (partner_user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (partner_code_id) REFERENCES partner_codes(id)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_commission_contracts_partner_account_id "
            "ON partner_commission_contracts(partner_account_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_commission_contracts_partner_user_id "
            "ON partner_commission_contracts(partner_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_commission_contracts_partner_code_id "
            "ON partner_commission_contracts(partner_code_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_commission_contracts_contract_status "
            "ON partner_commission_contracts(contract_status)"
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
            "CREATE INDEX ix_partner_traffic_declarations_reviewed_at ON partner_traffic_declarations(reviewed_at)"
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
        conn.exec_driver_sql("CREATE INDEX ix_creative_approvals_approval_kind ON creative_approvals(approval_kind)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_creative_approvals_approval_status ON creative_approvals(approval_status)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_creative_approvals_creative_ref ON creative_approvals(creative_ref)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_creative_approvals_submitted_by_admin_user_id "
            "ON creative_approvals(submitted_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_creative_approvals_reviewed_by_admin_user_id "
            "ON creative_approvals(reviewed_by_admin_user_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_creative_approvals_reviewed_at ON creative_approvals(reviewed_at)")
        conn.exec_driver_sql("CREATE INDEX ix_creative_approvals_expires_at ON creative_approvals(expires_at)")
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
                code_normalized TEXT UNIQUE,
                public_token_hash TEXT UNIQUE,
                public_slug TEXT UNIQUE,
                partner_account_id TEXT,
                partner_user_id TEXT,
                code_kind TEXT NOT NULL DEFAULT 'starter_code',
                lifecycle_status TEXT NOT NULL DEFAULT 'active',
                owner_type TEXT NOT NULL DEFAULT 'affiliate',
                lane_key TEXT NOT NULL DEFAULT 'creator_affiliate',
                attribution_model TEXT NOT NULL DEFAULT 'last_eligible_touch',
                attribution_window_seconds INTEGER NOT NULL DEFAULT 2592000,
                commission_contract_id TEXT,
                policy_version_id TEXT,
                default_storefront_id TEXT,
                destination_path TEXT,
                allowed_channels TEXT NOT NULL DEFAULT '["content","telegram","storefront"]',
                allowed_storefront_ids TEXT NOT NULL DEFAULT '["*"]',
                allowed_geographies TEXT NOT NULL DEFAULT '["*"]',
                sub_id_schema TEXT NOT NULL DEFAULT '{}',
                approval_status TEXT NOT NULL DEFAULT 'approved',
                markup_pct NUMERIC NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                active_from TEXT,
                expires_at TEXT,
                paused_at TEXT,
                revoked_at TEXT,
                created_by_admin_user_id TEXT,
                updated_by_admin_user_id TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (partner_user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (commission_contract_id) REFERENCES partner_commission_contracts(id),
                FOREIGN KEY (policy_version_id) REFERENCES policy_versions(id),
                FOREIGN KEY (default_storefront_id) REFERENCES storefronts(id),
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (updated_by_admin_user_id) REFERENCES admin_users(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_partner_codes_code_normalized ON partner_codes(code_normalized)")
        conn.exec_driver_sql("CREATE INDEX ix_partner_codes_public_token_hash ON partner_codes(public_token_hash)")
        conn.exec_driver_sql("CREATE INDEX ix_partner_codes_public_slug ON partner_codes(public_slug)")
        conn.exec_driver_sql("CREATE INDEX ix_partner_codes_partner_account_id ON partner_codes(partner_account_id)")
        conn.exec_driver_sql("CREATE INDEX ix_partner_codes_partner_user_id ON partner_codes(partner_user_id)")
        conn.exec_driver_sql("CREATE INDEX ix_partner_codes_lifecycle_status ON partner_codes(lifecycle_status)")
        conn.exec_driver_sql("CREATE INDEX ix_partner_codes_owner_type ON partner_codes(owner_type)")
        conn.exec_driver_sql("CREATE INDEX ix_partner_codes_lane_key ON partner_codes(lane_key)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_codes_commission_contract_id ON partner_codes(commission_contract_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_partner_codes_policy_version_id ON partner_codes(policy_version_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_codes_default_storefront_id ON partner_codes(default_storefront_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_partner_codes_approval_status ON partner_codes(approval_status)")
        conn.exec_driver_sql("CREATE INDEX ix_partner_codes_expires_at ON partner_codes(expires_at)")
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_code_links (
                id TEXT PRIMARY KEY,
                public_slug TEXT NOT NULL UNIQUE,
                partner_code_id TEXT NOT NULL,
                partner_account_id TEXT NOT NULL,
                link_kind TEXT NOT NULL DEFAULT 'deep_link',
                destination_key TEXT NOT NULL DEFAULT 'register',
                destination_path TEXT NOT NULL DEFAULT '/register',
                locale TEXT,
                sale_channel TEXT,
                campaign_params TEXT NOT NULL DEFAULT '{}',
                sub_ids TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'active',
                active_from TEXT,
                expires_at TEXT,
                created_by_admin_user_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_code_id) REFERENCES partner_codes(id),
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_partner_code_links_public_slug ON partner_code_links(public_slug)",
            "CREATE INDEX ix_partner_code_links_partner_code_id ON partner_code_links(partner_code_id)",
            "CREATE INDEX ix_partner_code_links_partner_account_id ON partner_code_links(partner_account_id)",
            "CREATE INDEX ix_partner_code_links_link_kind ON partner_code_links(link_kind)",
            "CREATE INDEX ix_partner_code_links_destination_key ON partner_code_links(destination_key)",
            "CREATE INDEX ix_partner_code_links_sale_channel ON partner_code_links(sale_channel)",
            "CREATE INDEX ix_partner_code_links_status ON partner_code_links(status)",
            "CREATE INDEX ix_partner_code_links_expires_at ON partner_code_links(expires_at)",
            "CREATE INDEX ix_partner_code_links_created_by_admin_user_id "
            "ON partner_code_links(created_by_admin_user_id)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_earnings (
                id TEXT PRIMARY KEY,
                partner_account_id TEXT,
                partner_user_id TEXT,
                client_user_id TEXT NOT NULL,
                payment_id TEXT NOT NULL,
                partner_code_id TEXT,
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
                partner_user_id TEXT,
                client_user_id TEXT NOT NULL,
                order_id TEXT NOT NULL UNIQUE,
                payment_id TEXT,
                source_event_id TEXT,
                source_event_key TEXT UNIQUE,
                partner_code_id TEXT,
                legacy_partner_earning_id TEXT,
                order_attribution_result_id TEXT,
                policy_version_id TEXT,
                commission_contract_id TEXT,
                owner_type TEXT NOT NULL,
                earning_component TEXT NOT NULL DEFAULT 'partner_cash',
                event_status TEXT NOT NULL DEFAULT 'on_hold',
                commission_base_amount NUMERIC NOT NULL,
                markup_amount NUMERIC NOT NULL,
                commission_pct NUMERIC NOT NULL,
                commission_amount NUMERIC NOT NULL,
                total_amount NUMERIC NOT NULL,
                currency_code TEXT NOT NULL DEFAULT 'USD',
                available_at TEXT,
                calculation_snapshot TEXT NOT NULL DEFAULT '{}',
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
                FOREIGN KEY (order_attribution_result_id) REFERENCES order_attribution_results(id),
                FOREIGN KEY (policy_version_id) REFERENCES policy_versions(id),
                FOREIGN KEY (commission_contract_id) REFERENCES partner_commission_contracts(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_partner_account_id ON earning_events(partner_account_id)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_partner_user_id ON earning_events(partner_user_id)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_client_user_id ON earning_events(client_user_id)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_order_id ON earning_events(order_id)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_payment_id ON earning_events(payment_id)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_source_event_id ON earning_events(source_event_id)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_source_event_key ON earning_events(source_event_key)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_partner_code_id ON earning_events(partner_code_id)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_earning_component ON earning_events(earning_component)")
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX uq_earning_events_payment_account_component "
            "ON earning_events(payment_id, partner_account_id, earning_component)"
        )
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX uq_earning_events_payment_user_component "
            "ON earning_events(payment_id, partner_user_id, earning_component)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_earning_events_legacy_partner_earning_id ON earning_events(legacy_partner_earning_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_earning_events_order_attribution_result_id ON earning_events(order_attribution_result_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_owner_type ON earning_events(owner_type)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_event_status ON earning_events(event_status)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_available_at ON earning_events(available_at)")
        conn.exec_driver_sql("CREATE INDEX ix_earning_events_policy_version_id ON earning_events(policy_version_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_earning_events_commission_contract_id ON earning_events(commission_contract_id)"
        )
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
        conn.exec_driver_sql("CREATE INDEX ix_reserves_created_by_admin_user_id ON reserves(created_by_admin_user_id)")
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
        conn.exec_driver_sql("CREATE INDEX ix_settlement_periods_period_key ON settlement_periods(period_key)")
        conn.exec_driver_sql("CREATE INDEX ix_settlement_periods_window_start ON settlement_periods(window_start)")
        conn.exec_driver_sql("CREATE INDEX ix_settlement_periods_window_end ON settlement_periods(window_end)")
        conn.exec_driver_sql("CREATE INDEX ix_settlement_periods_closed_at ON settlement_periods(closed_at)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_settlement_periods_closed_by_admin_user_id ON settlement_periods(closed_by_admin_user_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_settlement_periods_reopened_at ON settlement_periods(reopened_at)")
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
        conn.exec_driver_sql("CREATE INDEX ix_partner_statements_statement_key ON partner_statements(statement_key)")
        conn.exec_driver_sql("CREATE INDEX ix_partner_statements_closed_at ON partner_statements(closed_at)")
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
            "CREATE INDEX ix_partner_payout_accounts_partner_account_id ON partner_payout_accounts(partner_account_id)"
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
            "CREATE INDEX ix_partner_payout_accounts_approval_status ON partner_payout_accounts(approval_status)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_account_status ON partner_payout_accounts(account_status)"
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
            "CREATE INDEX ix_partner_payout_accounts_verified_at ON partner_payout_accounts(verified_at)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_approved_by_admin_user_id "
            "ON partner_payout_accounts(approved_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_approved_at ON partner_payout_accounts(approved_at)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_suspended_by_admin_user_id "
            "ON partner_payout_accounts(suspended_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_suspended_at ON partner_payout_accounts(suspended_at)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_archived_by_admin_user_id "
            "ON partner_payout_accounts(archived_by_admin_user_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_payout_accounts_archived_at ON partner_payout_accounts(archived_at)"
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
        conn.exec_driver_sql("CREATE INDEX ix_payout_instructions_approved_at ON payout_instructions(approved_at)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_instructions_rejected_by_admin_user_id "
            "ON payout_instructions(rejected_by_admin_user_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_payout_instructions_rejected_at ON payout_instructions(rejected_at)")
        conn.exec_driver_sql("CREATE INDEX ix_payout_instructions_completed_at ON payout_instructions(completed_at)")
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
            "CREATE INDEX ix_payout_executions_payout_instruction_id ON payout_executions(payout_instruction_id)"
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
        conn.exec_driver_sql("CREATE INDEX ix_payout_executions_execution_key ON payout_executions(execution_key)")
        conn.exec_driver_sql("CREATE INDEX ix_payout_executions_execution_mode ON payout_executions(execution_mode)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_execution_status ON payout_executions(execution_status)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_request_idempotency_key ON payout_executions(request_idempotency_key)"
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
        conn.exec_driver_sql("CREATE INDEX ix_payout_executions_submitted_at ON payout_executions(submitted_at)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_completed_by_admin_user_id "
            "ON payout_executions(completed_by_admin_user_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_payout_executions_completed_at ON payout_executions(completed_at)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_payout_executions_reconciled_by_admin_user_id "
            "ON payout_executions(reconciled_by_admin_user_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_payout_executions_reconciled_at ON payout_executions(reconciled_at)")
        conn.exec_driver_sql(
            """
            CREATE TABLE user_devices (
                id TEXT PRIMARY KEY,
                auth_realm_id TEXT NOT NULL,
                principal_subject TEXT NOT NULL,
                principal_class TEXT NOT NULL,
                audience TEXT NOT NULL,
                device_key_hash TEXT NOT NULL,
                device_label TEXT,
                platform TEXT,
                ip_address TEXT,
                user_agent TEXT,
                first_user_agent TEXT,
                last_user_agent TEXT,
                last_ip_address TEXT,
                last_ip_source TEXT,
                last_proxy_peer TEXT,
                first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                revoked_at TEXT,
                revoked_reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_user_devices_auth_realm_id ON user_devices(auth_realm_id)")
        conn.exec_driver_sql("CREATE INDEX ix_user_devices_principal_subject ON user_devices(principal_subject)")
        conn.exec_driver_sql("CREATE INDEX ix_user_devices_principal_class ON user_devices(principal_class)")
        conn.exec_driver_sql("CREATE INDEX ix_user_devices_audience ON user_devices(audience)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_user_devices_principal ON user_devices(auth_realm_id, principal_class, principal_subject)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_user_devices_last_seen_at ON user_devices(last_seen_at)")
        conn.exec_driver_sql("CREATE INDEX ix_user_devices_revoked_at ON user_devices(revoked_at)")
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX uq_user_devices_active_principal_device_key "
            "ON user_devices(auth_realm_id, principal_class, principal_subject, device_key_hash) "
            "WHERE revoked_at IS NULL"
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
                user_device_id TEXT,
                current_refresh_token_id TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                issued_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (refresh_token_id) REFERENCES refresh_tokens(id),
                FOREIGN KEY (user_device_id) REFERENCES user_devices(id),
                FOREIGN KEY (current_refresh_token_id) REFERENCES refresh_tokens(id)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_principal_sessions_principal_subject ON principal_sessions(principal_subject)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_principal_sessions_refresh_token_id ON principal_sessions(refresh_token_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_principal_sessions_user_device_id ON principal_sessions(user_device_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_principal_sessions_user_device_status ON principal_sessions(user_device_id, status)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_principal_sessions_current_refresh_token_id "
            "ON principal_sessions(current_refresh_token_id)"
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
            "CREATE INDEX ix_risk_review_attachments_risk_review_id ON risk_review_attachments(risk_review_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_risk_review_attachments_attachment_type ON risk_review_attachments(attachment_type)"
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
        conn.exec_driver_sql("CREATE INDEX ix_governance_actions_risk_review_id ON governance_actions(risk_review_id)")
        conn.exec_driver_sql("CREATE INDEX ix_governance_actions_action_type ON governance_actions(action_type)")
        conn.exec_driver_sql("CREATE INDEX ix_governance_actions_action_status ON governance_actions(action_status)")
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
                code_set_id TEXT,
                private_catalog_access_grant_id TEXT,
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
        conn.exec_driver_sql("CREATE INDEX ix_quote_sessions_code_set_id ON quote_sessions(code_set_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_quote_sessions_private_catalog_access_grant_id "
            "ON quote_sessions(private_catalog_access_grant_id)"
        )
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
                code_set_id TEXT,
                private_catalog_access_grant_id TEXT,
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
            "CREATE INDEX ix_checkout_sessions_quote_session_id ON checkout_sessions(quote_session_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_checkout_sessions_user_id ON checkout_sessions(user_id)")
        conn.exec_driver_sql("CREATE INDEX ix_checkout_sessions_auth_realm_id ON checkout_sessions(auth_realm_id)")
        conn.exec_driver_sql("CREATE INDEX ix_checkout_sessions_storefront_id ON checkout_sessions(storefront_id)")
        conn.exec_driver_sql("CREATE INDEX ix_checkout_sessions_code_set_id ON checkout_sessions(code_set_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_checkout_sessions_private_catalog_access_grant_id "
            "ON checkout_sessions(private_catalog_access_grant_id)"
        )
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
                code_set_id TEXT,
                private_catalog_access_grant_id TEXT,
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
                risk_snapshot TEXT NOT NULL DEFAULT '{}',
                fx_snapshot TEXT NOT NULL DEFAULT '{}',
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
        conn.exec_driver_sql("CREATE INDEX ix_orders_code_set_id ON orders(code_set_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_orders_private_catalog_access_grant_id ON orders(private_catalog_access_grant_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_orders_order_status ON orders(order_status)")
        conn.exec_driver_sql("CREATE INDEX ix_orders_settlement_status ON orders(settlement_status)")
        conn.exec_driver_sql(
            """
            CREATE TABLE growth_private_catalog_policies (
                id TEXT PRIMARY KEY,
                policy_version_id TEXT NOT NULL,
                growth_code_id TEXT NOT NULL,
                unlock_mode TEXT NOT NULL,
                target_plan_ids TEXT NOT NULL DEFAULT '[]',
                target_offer_ids TEXT NOT NULL DEFAULT '[]',
                target_offer_keys TEXT NOT NULL DEFAULT '[]',
                auto_select_target_id TEXT,
                allowed_storefront_ids TEXT NOT NULL DEFAULT '[]',
                allowed_channels TEXT NOT NULL DEFAULT '[]',
                grant_ttl_seconds INTEGER NOT NULL,
                max_quote_conversions INTEGER,
                consume_mode TEXT NOT NULL,
                requires_auth INTEGER NOT NULL DEFAULT 1,
                requires_risk_action_below TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (policy_version_id) REFERENCES policy_versions(id) ON DELETE CASCADE,
                FOREIGN KEY (growth_code_id) REFERENCES growth_codes(id) ON DELETE CASCADE,
                CHECK (grant_ttl_seconds > 0),
                CHECK (max_quote_conversions IS NULL OR max_quote_conversions >= 0)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_growth_private_catalog_policies_policy_version_id "
            "ON growth_private_catalog_policies(policy_version_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_growth_private_catalog_policies_growth_code_id "
            "ON growth_private_catalog_policies(growth_code_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_growth_private_catalog_policies_is_active ON growth_private_catalog_policies(is_active)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE private_catalog_access_grants (
                id TEXT PRIMARY KEY,
                policy_id TEXT NOT NULL,
                policy_version_id TEXT NOT NULL,
                growth_code_id TEXT NOT NULL,
                code_set_hash TEXT NOT NULL,
                grant_token_hash TEXT UNIQUE,
                user_id TEXT,
                anonymous_session_id TEXT,
                risk_subject_id TEXT,
                auth_realm_id TEXT NOT NULL,
                storefront_id TEXT NOT NULL,
                sale_channel TEXT NOT NULL,
                allowed_plan_ids TEXT NOT NULL DEFAULT '[]',
                allowed_offer_ids TEXT NOT NULL DEFAULT '[]',
                risk_decision_id TEXT,
                status TEXT NOT NULL,
                max_quote_conversions INTEGER,
                quote_conversions_count INTEGER NOT NULL DEFAULT 0,
                issued_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                attached_quote_session_id TEXT,
                attached_checkout_session_id TEXT,
                consumed_order_id TEXT,
                revoked_at TEXT,
                revoked_reason TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (policy_id) REFERENCES growth_private_catalog_policies(id) ON DELETE RESTRICT,
                FOREIGN KEY (policy_version_id) REFERENCES policy_versions(id) ON DELETE RESTRICT,
                FOREIGN KEY (growth_code_id) REFERENCES growth_codes(id) ON DELETE RESTRICT,
                FOREIGN KEY (user_id) REFERENCES mobile_users(id) ON DELETE SET NULL,
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id) ON DELETE RESTRICT,
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id) ON DELETE RESTRICT,
                FOREIGN KEY (attached_quote_session_id) REFERENCES quote_sessions(id) ON DELETE SET NULL,
                FOREIGN KEY (attached_checkout_session_id) REFERENCES checkout_sessions(id) ON DELETE SET NULL,
                FOREIGN KEY (consumed_order_id) REFERENCES orders(id) ON DELETE SET NULL,
                CHECK (user_id IS NOT NULL OR anonymous_session_id IS NOT NULL),
                CHECK (quote_conversions_count >= 0),
                CHECK (max_quote_conversions IS NULL OR quote_conversions_count <= max_quote_conversions)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_private_catalog_access_grants_policy_id ON private_catalog_access_grants(policy_id)",
            "CREATE INDEX ix_private_catalog_access_grants_policy_version_id "
            "ON private_catalog_access_grants(policy_version_id)",
            "CREATE INDEX ix_private_catalog_access_grants_growth_code_id "
            "ON private_catalog_access_grants(growth_code_id)",
            "CREATE INDEX ix_private_catalog_access_grants_code_set_hash "
            "ON private_catalog_access_grants(code_set_hash)",
            "CREATE INDEX ix_private_catalog_access_grants_grant_token_hash "
            "ON private_catalog_access_grants(grant_token_hash)",
            "CREATE INDEX ix_private_catalog_access_grants_user_id ON private_catalog_access_grants(user_id)",
            "CREATE INDEX ix_private_catalog_access_grants_anonymous_session_id "
            "ON private_catalog_access_grants(anonymous_session_id)",
            "CREATE INDEX ix_private_catalog_access_grants_auth_realm_id "
            "ON private_catalog_access_grants(auth_realm_id)",
            "CREATE INDEX ix_private_catalog_access_grants_storefront_id "
            "ON private_catalog_access_grants(storefront_id)",
            "CREATE INDEX ix_private_catalog_access_grants_sale_channel ON private_catalog_access_grants(sale_channel)",
            "CREATE INDEX ix_private_catalog_access_grants_status ON private_catalog_access_grants(status)",
            "CREATE INDEX ix_private_catalog_access_grants_expires_at ON private_catalog_access_grants(expires_at)",
            "CREATE INDEX ix_private_catalog_access_grants_attached_quote_session_id "
            "ON private_catalog_access_grants(attached_quote_session_id)",
            "CREATE INDEX ix_private_catalog_access_grants_attached_checkout_session_id "
            "ON private_catalog_access_grants(attached_checkout_session_id)",
            "CREATE INDEX ix_private_catalog_access_grants_consumed_order_id "
            "ON private_catalog_access_grants(consumed_order_id)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE checkout_code_sets (
                id TEXT PRIMARY KEY,
                code_set_hash TEXT NOT NULL,
                user_id TEXT,
                anonymous_session_id TEXT,
                auth_realm_id TEXT NOT NULL,
                storefront_id TEXT,
                sale_channel TEXT NOT NULL,
                action_context TEXT NOT NULL,
                status TEXT NOT NULL,
                acceptance_mode TEXT NOT NULL,
                aggregate_result TEXT NOT NULL DEFAULT '{}',
                risk_snapshot TEXT NOT NULL DEFAULT '{}',
                private_access_grant_id TEXT,
                quote_session_id TEXT,
                checkout_session_id TEXT,
                order_id TEXT,
                payment_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES mobile_users(id) ON DELETE SET NULL,
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id) ON DELETE SET NULL,
                FOREIGN KEY (quote_session_id) REFERENCES quote_sessions(id) ON DELETE SET NULL,
                FOREIGN KEY (checkout_session_id) REFERENCES checkout_sessions(id) ON DELETE SET NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_checkout_code_sets_code_set_hash ON checkout_code_sets(code_set_hash)",
            "CREATE INDEX ix_checkout_code_sets_user_id ON checkout_code_sets(user_id)",
            "CREATE INDEX ix_checkout_code_sets_auth_realm_id ON checkout_code_sets(auth_realm_id)",
            "CREATE INDEX ix_checkout_code_sets_storefront_id ON checkout_code_sets(storefront_id)",
            "CREATE INDEX ix_checkout_code_sets_status ON checkout_code_sets(status)",
            "CREATE INDEX ix_checkout_code_sets_quote_session_id ON checkout_code_sets(quote_session_id)",
            "CREATE INDEX ix_checkout_code_sets_checkout_session_id ON checkout_code_sets(checkout_session_id)",
            "CREATE INDEX ix_checkout_code_sets_order_id ON checkout_code_sets(order_id)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE checkout_code_applications (
                id TEXT PRIMARY KEY,
                code_set_id TEXT NOT NULL,
                position_entered INTEGER NOT NULL,
                canonical_order INTEGER NOT NULL,
                growth_code_id TEXT,
                legacy_code_type TEXT,
                legacy_code_id TEXT,
                masked_code TEXT NOT NULL,
                roles TEXT NOT NULL DEFAULT '{}',
                resolution_status TEXT NOT NULL,
                reject_reason TEXT,
                conflict_code TEXT,
                policy_version_id TEXT,
                rule_definition_id TEXT,
                risk_decision_id TEXT,
                fx_conversion_id TEXT,
                reservation_id TEXT,
                discount_snapshot TEXT NOT NULL DEFAULT '{}',
                benefits_snapshot TEXT NOT NULL DEFAULT '{}',
                private_access_snapshot TEXT NOT NULL DEFAULT '{}',
                evaluation_trace TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (code_set_id) REFERENCES checkout_code_sets(id) ON DELETE CASCADE,
                FOREIGN KEY (growth_code_id) REFERENCES growth_codes(id) ON DELETE SET NULL,
                FOREIGN KEY (policy_version_id) REFERENCES policy_versions(id) ON DELETE SET NULL,
                FOREIGN KEY (reservation_id) REFERENCES growth_code_reservations(id) ON DELETE SET NULL,
                UNIQUE (code_set_id, growth_code_id)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_checkout_code_applications_code_set_id ON checkout_code_applications(code_set_id)",
            "CREATE INDEX ix_checkout_code_applications_growth_code_id ON checkout_code_applications(growth_code_id)",
            "CREATE INDEX ix_checkout_code_applications_legacy_code_id ON checkout_code_applications(legacy_code_id)",
            "CREATE INDEX ix_checkout_code_applications_resolution_status "
            "ON checkout_code_applications(resolution_status)",
            "CREATE INDEX ix_checkout_code_applications_reservation_id ON checkout_code_applications(reservation_id)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE order_code_applications (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                code_set_id TEXT NOT NULL,
                growth_code_id TEXT NOT NULL,
                policy_version_id TEXT,
                application_role TEXT NOT NULL,
                application_status TEXT NOT NULL,
                discount_amount NUMERIC NOT NULL,
                currency_code TEXT NOT NULL,
                source_amount NUMERIC,
                source_currency_code TEXT,
                fx_conversion_id TEXT,
                reservation_id TEXT,
                risk_decision_id TEXT,
                application_snapshot TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (code_set_id) REFERENCES checkout_code_sets(id),
                FOREIGN KEY (growth_code_id) REFERENCES growth_codes(id),
                FOREIGN KEY (policy_version_id) REFERENCES policy_versions(id) ON DELETE SET NULL,
                FOREIGN KEY (reservation_id) REFERENCES growth_code_reservations(id) ON DELETE SET NULL,
                UNIQUE (order_id, growth_code_id)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_order_code_applications_order_id ON order_code_applications(order_id)",
            "CREATE INDEX ix_order_code_applications_code_set_id ON order_code_applications(code_set_id)",
            "CREATE INDEX ix_order_code_applications_growth_code_id ON order_code_applications(growth_code_id)",
            "CREATE INDEX ix_order_code_applications_policy_version_id ON order_code_applications(policy_version_id)",
            "CREATE INDEX ix_order_code_applications_application_role ON order_code_applications(application_role)",
            "CREATE INDEX ix_order_code_applications_application_status ON order_code_applications(application_status)",
            "CREATE INDEX ix_order_code_applications_reservation_id ON order_code_applications(reservation_id)",
        ):
            conn.exec_driver_sql(index_sql)
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
            CREATE TABLE partner_attribution_sessions (
                id TEXT PRIMARY KEY,
                session_token_hash TEXT UNIQUE,
                transfer_token_hash TEXT UNIQUE,
                consumed_transfer_token_hash TEXT UNIQUE,
                transfer_expires_at TEXT,
                transfer_consumed_at TEXT,
                partner_code_id TEXT NOT NULL,
                partner_code_link_id TEXT,
                partner_account_id TEXT,
                auth_realm_id TEXT,
                storefront_id TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                owner_type TEXT NOT NULL DEFAULT 'affiliate',
                attribution_model TEXT NOT NULL DEFAULT 'last_eligible_touch',
                policy_version_id TEXT,
                commission_contract_id TEXT,
                source_host TEXT,
                source_path TEXT,
                destination_path TEXT,
                locale TEXT NOT NULL DEFAULT 'ru-RU',
                sale_channel TEXT,
                sub_ids TEXT NOT NULL DEFAULT '{}',
                click_id TEXT,
                browser_key_hash TEXT,
                capture_idempotency_key_hash TEXT UNIQUE,
                destination_url TEXT NOT NULL,
                campaign_params TEXT NOT NULL DEFAULT '{}',
                evidence_payload TEXT NOT NULL DEFAULT '{}',
                policy_snapshot TEXT NOT NULL DEFAULT '{}',
                rejection_reason_code TEXT,
                user_id TEXT,
                touchpoint_id TEXT,
                binding_id TEXT,
                expires_at TEXT NOT NULL,
                first_seen_at TEXT,
                last_seen_at TEXT,
                transferred_at TEXT,
                claimed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_code_id) REFERENCES partner_codes(id),
                FOREIGN KEY (partner_code_link_id) REFERENCES partner_code_links(id),
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id),
                FOREIGN KEY (policy_version_id) REFERENCES policy_versions(id),
                FOREIGN KEY (commission_contract_id) REFERENCES partner_commission_contracts(id),
                FOREIGN KEY (user_id) REFERENCES mobile_users(id)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_partner_attr_sessions_session_token_hash "
            "ON partner_attribution_sessions(session_token_hash)",
            "CREATE INDEX ix_partner_attr_sessions_transfer_token_hash "
            "ON partner_attribution_sessions(transfer_token_hash)",
            "CREATE INDEX ix_partner_attr_sessions_consumed_transfer_token_hash "
            "ON partner_attribution_sessions(consumed_transfer_token_hash)",
            "CREATE INDEX ix_partner_attr_sessions_transfer_expires_at "
            "ON partner_attribution_sessions(transfer_expires_at)",
            "CREATE INDEX ix_partner_attr_sessions_partner_code_id ON partner_attribution_sessions(partner_code_id)",
            "CREATE INDEX ix_partner_attr_sessions_partner_code_link_id "
            "ON partner_attribution_sessions(partner_code_link_id)",
            "CREATE INDEX ix_partner_attr_sessions_partner_account_id "
            "ON partner_attribution_sessions(partner_account_id)",
            "CREATE INDEX ix_partner_attr_sessions_auth_realm_id ON partner_attribution_sessions(auth_realm_id)",
            "CREATE INDEX ix_partner_attr_sessions_storefront_id ON partner_attribution_sessions(storefront_id)",
            "CREATE INDEX ix_partner_attr_sessions_policy_version_id "
            "ON partner_attribution_sessions(policy_version_id)",
            "CREATE INDEX ix_partner_attr_sessions_user_id ON partner_attribution_sessions(user_id)",
            "CREATE INDEX ix_partner_attr_sessions_touchpoint_id ON partner_attribution_sessions(touchpoint_id)",
            "CREATE INDEX ix_partner_attr_sessions_binding_id ON partner_attribution_sessions(binding_id)",
            "CREATE INDEX ix_partner_attr_sessions_sale_channel ON partner_attribution_sessions(sale_channel)",
            "CREATE INDEX ix_partner_attr_sessions_click_id ON partner_attribution_sessions(click_id)",
            "CREATE INDEX ix_partner_attr_sessions_browser_key_hash ON partner_attribution_sessions(browser_key_hash)",
            "CREATE INDEX ix_partner_attr_sessions_capture_idempotency_key_hash "
            "ON partner_attribution_sessions(capture_idempotency_key_hash)",
            "CREATE INDEX ix_partner_attr_sessions_expires_at ON partner_attribution_sessions(expires_at)",
            "CREATE INDEX ix_partner_attr_sessions_last_seen_at ON partner_attribution_sessions(last_seen_at)",
            "CREATE INDEX ix_partner_attr_sessions_created_at ON partner_attribution_sessions(created_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE partner_code_events (
                id TEXT PRIMARY KEY,
                partner_code_id TEXT NOT NULL,
                partner_account_id TEXT,
                event_type TEXT NOT NULL,
                previous_status TEXT,
                next_status TEXT,
                reason_code TEXT,
                actor_principal_id TEXT,
                event_payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_code_id) REFERENCES partner_codes(id),
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id)
            )
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_code_events_partner_code_id ON partner_code_events(partner_code_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_code_events_partner_account_id ON partner_code_events(partner_account_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_partner_code_events_event_type ON partner_code_events(event_type)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_partner_code_events_actor_principal_id ON partner_code_events(actor_principal_id)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE api_idempotency_records (
                id TEXT PRIMARY KEY,
                scope TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT,
                request_hash TEXT,
                response_payload TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'completed',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT,
                UNIQUE(scope, idempotency_key)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_api_idempotency_records_scope ON api_idempotency_records(scope)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_api_idempotency_records_resource_id ON api_idempotency_records(resource_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_api_idempotency_records_created_at ON api_idempotency_records(created_at)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_api_idempotency_records_expires_at ON api_idempotency_records(expires_at)"
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE attribution_touchpoints (
                id TEXT PRIMARY KEY,
                touchpoint_type TEXT NOT NULL,
                source_event_id TEXT,
                idempotency_key TEXT,
                partner_attribution_session_id TEXT,
                user_id TEXT,
                auth_realm_id TEXT,
                storefront_id TEXT,
                quote_session_id TEXT,
                checkout_session_id TEXT,
                order_id TEXT,
                partner_code_id TEXT,
                policy_version_id TEXT,
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
                FOREIGN KEY (partner_code_id) REFERENCES partner_codes(id),
                FOREIGN KEY (policy_version_id) REFERENCES policy_versions(id),
                FOREIGN KEY (partner_attribution_session_id) REFERENCES partner_attribution_sessions(id)
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
            "CREATE INDEX ix_attribution_touchpoints_partner_attr_session_id "
            "ON attribution_touchpoints(partner_attribution_session_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_attribution_touchpoints_policy_version_id ON attribution_touchpoints(policy_version_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_attribution_touchpoints_source_event_id ON attribution_touchpoints(source_event_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_attribution_touchpoints_idempotency_key ON attribution_touchpoints(idempotency_key)"
        )
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX uq_attribution_touchpoints_realm_idempotency_key "
            "ON attribution_touchpoints(auth_realm_id, idempotency_key) "
            "WHERE idempotency_key IS NOT NULL"
        )
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX uq_attribution_touchpoints_realm_source_event_id "
            "ON attribution_touchpoints(auth_realm_id, source_event_id) "
            "WHERE source_event_id IS NOT NULL"
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
                policy_version_id TEXT,
                commission_contract_id TEXT,
                attribution_session_id TEXT,
                reason_code TEXT,
                evidence_payload TEXT NOT NULL DEFAULT '{}',
                created_by_admin_user_id TEXT,
                effective_from TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                effective_to TEXT,
                claimed_at TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES mobile_users(id),
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id),
                FOREIGN KEY (partner_account_id) REFERENCES partner_accounts(id),
                FOREIGN KEY (partner_code_id) REFERENCES partner_codes(id),
                FOREIGN KEY (policy_version_id) REFERENCES policy_versions(id),
                FOREIGN KEY (commission_contract_id) REFERENCES partner_commission_contracts(id),
                FOREIGN KEY (attribution_session_id) REFERENCES partner_attribution_sessions(id),
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
            "CREATE INDEX ix_customer_commercial_bindings_policy_version_id "
            "ON customer_commercial_bindings(policy_version_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_customer_commercial_bindings_commission_contract_id "
            "ON customer_commercial_bindings(commission_contract_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_customer_commercial_bindings_attribution_session_id "
            "ON customer_commercial_bindings(attribution_session_id)"
        )
        conn.exec_driver_sql(
            "CREATE INDEX ix_customer_commercial_bindings_claimed_at ON customer_commercial_bindings(claimed_at)"
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
                attribution_session_id TEXT,
                policy_version_id TEXT,
                commission_contract_id TEXT,
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
                FOREIGN KEY (attribution_session_id) REFERENCES partner_attribution_sessions(id),
                FOREIGN KEY (policy_version_id) REFERENCES policy_versions(id),
                FOREIGN KEY (commission_contract_id) REFERENCES partner_commission_contracts(id),
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
            "CREATE INDEX ix_order_attribution_results_attribution_session_id "
            "ON order_attribution_results(attribution_session_id)",
            "CREATE INDEX ix_order_attribution_results_policy_version_id "
            "ON order_attribution_results(policy_version_id)",
            "CREATE INDEX ix_order_attribution_results_commission_contract_id "
            "ON order_attribution_results(commission_contract_id)",
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
            "CREATE INDEX ix_renewal_orders_provenance_partner_code_id ON renewal_orders(provenance_partner_code_id)",
            "CREATE INDEX ix_renewal_orders_effective_partner_account_id "
            "ON renewal_orders(effective_partner_account_id)",
            "CREATE INDEX ix_renewal_orders_effective_partner_code_id ON renewal_orders(effective_partner_code_id)",
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
                code_set_id TEXT,
                discount_amount NUMERIC NOT NULL DEFAULT 0,
                wallet_amount_used NUMERIC NOT NULL DEFAULT 0,
                final_amount NUMERIC,
                addons_snapshot TEXT,
                entitlements_snapshot TEXT,
                growth_snapshot TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK (provider <> 'internal_zero' OR external_id IS NOT NULL),
                FOREIGN KEY (code_set_id) REFERENCES checkout_code_sets(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_payments_external_id ON payments(external_id)")
        conn.exec_driver_sql("CREATE INDEX ix_payments_user_uuid ON payments(user_uuid)")
        conn.exec_driver_sql("CREATE INDEX ix_payments_status ON payments(status)")
        conn.exec_driver_sql("CREATE INDEX ix_payments_code_set_id ON payments(code_set_id)")
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX uq_payments_internal_zero_external_id "
            "ON payments(provider, external_id) "
            "WHERE provider = 'internal_zero' AND external_id IS NOT NULL"
        )
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
                code_set_id TEXT,
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
                FOREIGN KEY (code_set_id) REFERENCES checkout_code_sets(id),
                FOREIGN KEY (supersedes_attempt_id) REFERENCES payment_attempts(id)
            )
            """
        )
        conn.exec_driver_sql("CREATE INDEX ix_payment_attempts_order_id ON payment_attempts(order_id)")
        conn.exec_driver_sql("CREATE INDEX ix_payment_attempts_payment_id ON payment_attempts(payment_id)")
        conn.exec_driver_sql("CREATE INDEX ix_payment_attempts_code_set_id ON payment_attempts(code_set_id)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_payment_attempts_supersedes_attempt_id ON payment_attempts(supersedes_attempt_id)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_payment_attempts_status ON payment_attempts(status)")
        conn.exec_driver_sql(
            "CREATE INDEX ix_payment_attempts_external_reference ON payment_attempts(external_reference)"
        )
        conn.exec_driver_sql("CREATE INDEX ix_payment_attempts_idempotency_key ON payment_attempts(idempotency_key)")
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX uq_payment_attempts_order_attempt_number ON payment_attempts(order_id, attempt_number)"
        )
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX uq_payment_attempts_order_active "
            "ON payment_attempts(order_id) "
            "WHERE status IN ('pending', 'processing')"
        )
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX uq_payment_attempts_order_succeeded "
            "ON payment_attempts(order_id) "
            "WHERE status = 'succeeded'"
        )
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
            "CREATE INDEX ix_partner_application_review_requests_status ON partner_application_review_requests(status)",
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
            "CREATE INDEX ix_partner_application_attachments_created_at ON partner_application_attachments(created_at)",
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
            CREATE TABLE customer_growth_notification_read_states (
                id TEXT PRIMARY KEY,
                mobile_user_id TEXT NOT NULL,
                notification_key TEXT NOT NULL,
                read_at TEXT,
                archived_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mobile_user_id) REFERENCES mobile_users(id) ON DELETE CASCADE,
                UNIQUE (mobile_user_id, notification_key)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_customer_growth_notification_read_states_mobile_user_id "
            "ON customer_growth_notification_read_states(mobile_user_id)",
            "CREATE INDEX ix_customer_growth_notification_read_states_notification_key "
            "ON customer_growth_notification_read_states(notification_key)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE customer_growth_notification_deliveries (
                id TEXT PRIMARY KEY,
                mobile_user_id TEXT NOT NULL,
                notification_key TEXT NOT NULL,
                notification_kind TEXT NOT NULL,
                delivery_channel TEXT NOT NULL,
                delivery_status TEXT NOT NULL,
                status_reason TEXT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                delivery_payload TEXT NOT NULL DEFAULT '{}',
                source_kind TEXT,
                source_id TEXT,
                notification_queue_id TEXT,
                created_by_admin_user_id TEXT,
                planned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                delivered_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mobile_user_id) REFERENCES mobile_users(id) ON DELETE CASCADE,
                FOREIGN KEY (notification_queue_id) REFERENCES notification_queue(id) ON DELETE SET NULL,
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL,
                UNIQUE (mobile_user_id, notification_key, delivery_channel)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_customer_growth_notification_deliveries_mobile_user_id "
            "ON customer_growth_notification_deliveries(mobile_user_id)",
            "CREATE INDEX ix_customer_growth_notification_deliveries_notification_key "
            "ON customer_growth_notification_deliveries(notification_key)",
            "CREATE INDEX ix_customer_growth_notification_deliveries_notification_kind "
            "ON customer_growth_notification_deliveries(notification_kind)",
            "CREATE INDEX ix_customer_growth_notification_deliveries_delivery_channel "
            "ON customer_growth_notification_deliveries(delivery_channel)",
            "CREATE INDEX ix_customer_growth_notification_deliveries_delivery_status "
            "ON customer_growth_notification_deliveries(delivery_status)",
            "CREATE INDEX ix_customer_growth_notification_deliveries_notification_queue_id "
            "ON customer_growth_notification_deliveries(notification_queue_id)",
            "CREATE INDEX ix_customer_growth_notification_deliveries_created_by_admin_user_id "
            "ON customer_growth_notification_deliveries(created_by_admin_user_id)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE customer_growth_notification_delivery_events (
                id TEXT PRIMARY KEY,
                delivery_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                delivery_status TEXT NOT NULL,
                reason_code TEXT,
                event_payload TEXT NOT NULL DEFAULT '{}',
                event_note TEXT,
                notification_queue_id TEXT,
                created_by_admin_user_id TEXT,
                occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (delivery_id) REFERENCES customer_growth_notification_deliveries(id) ON DELETE CASCADE,
                FOREIGN KEY (notification_queue_id) REFERENCES notification_queue(id) ON DELETE SET NULL,
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_customer_growth_notification_delivery_events_delivery_id "
            "ON customer_growth_notification_delivery_events(delivery_id)",
            "CREATE INDEX ix_customer_growth_notification_delivery_events_event_type "
            "ON customer_growth_notification_delivery_events(event_type)",
            "CREATE INDEX ix_customer_growth_notification_delivery_events_delivery_status "
            "ON customer_growth_notification_delivery_events(delivery_status)",
            "CREATE INDEX ix_customer_growth_notification_delivery_events_notification_queue_id "
            "ON customer_growth_notification_delivery_events(notification_queue_id)",
            "CREATE INDEX ix_customer_growth_notification_delivery_events_created_by_admin_user_id "
            "ON customer_growth_notification_delivery_events(created_by_admin_user_id)",
            "CREATE INDEX ix_customer_growth_notification_delivery_events_occurred_at "
            "ON customer_growth_notification_delivery_events(occurred_at)",
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
            "CREATE INDEX ix_pilot_owner_acknowledgements_owner_team ON pilot_owner_acknowledgements(owner_team)",
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
            "CREATE INDEX ix_pilot_rollback_drills_rollback_scope_class ON pilot_rollback_drills(rollback_scope_class)",
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
            "CREATE INDEX ix_pilot_go_no_go_decisions_pilot_cohort_id ON pilot_go_no_go_decisions(pilot_cohort_id)",
            "CREATE INDEX ix_pilot_go_no_go_decisions_decision_status ON pilot_go_no_go_decisions(decision_status)",
            "CREATE INDEX ix_pilot_go_no_go_decisions_rollback_scope_class "
            "ON pilot_go_no_go_decisions(rollback_scope_class)",
            "CREATE INDEX ix_pilot_go_no_go_decisions_decided_by_admin_user_id "
            "ON pilot_go_no_go_decisions(decided_by_admin_user_id)",
            "CREATE INDEX ix_pilot_go_no_go_decisions_decided_at ON pilot_go_no_go_decisions(decided_at)",
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
                source_code_id TEXT,
                source_redemption_id TEXT UNIQUE,
                policy_version_id TEXT,
                order_id TEXT,
                invite_code_id TEXT,
                referral_commission_id TEXT,
                source_key TEXT UNIQUE,
                quantity NUMERIC NOT NULL DEFAULT 1,
                unit TEXT NOT NULL,
                currency_code TEXT,
                reward_payload TEXT NOT NULL DEFAULT '{}',
                hold_until TEXT,
                available_at TEXT,
                reversal_reason TEXT,
                wallet_transaction_id TEXT,
                created_by_admin_user_id TEXT,
                allocated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reversed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (beneficiary_user_id) REFERENCES mobile_users(id) ON DELETE CASCADE,
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id) ON DELETE CASCADE,
                FOREIGN KEY (storefront_id) REFERENCES storefronts(id) ON DELETE SET NULL,
                FOREIGN KEY (source_code_id) REFERENCES growth_codes(id) ON DELETE SET NULL,
                FOREIGN KEY (source_redemption_id) REFERENCES growth_code_redemptions(id) ON DELETE SET NULL,
                FOREIGN KEY (policy_version_id) REFERENCES policy_versions(id) ON DELETE SET NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL,
                FOREIGN KEY (invite_code_id) REFERENCES invite_codes(id) ON DELETE SET NULL,
                FOREIGN KEY (referral_commission_id) REFERENCES referral_commissions(id) ON DELETE SET NULL,
                FOREIGN KEY (wallet_transaction_id) REFERENCES wallet_transactions(id) ON DELETE SET NULL,
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id) ON DELETE SET NULL
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
            "CREATE INDEX ix_growth_reward_allocations_source_code_id ON growth_reward_allocations(source_code_id)",
            "CREATE INDEX ix_growth_reward_allocations_source_redemption_id "
            "ON growth_reward_allocations(source_redemption_id)",
            "CREATE INDEX ix_growth_reward_allocations_policy_version_id "
            "ON growth_reward_allocations(policy_version_id)",
            "CREATE INDEX ix_growth_reward_allocations_order_id ON growth_reward_allocations(order_id)",
            "CREATE INDEX ix_growth_reward_allocations_invite_code_id ON growth_reward_allocations(invite_code_id)",
            "CREATE INDEX ix_growth_reward_allocations_referral_commission_id "
            "ON growth_reward_allocations(referral_commission_id)",
            "CREATE INDEX ix_growth_reward_allocations_hold_until ON growth_reward_allocations(hold_until)",
            "CREATE INDEX ix_growth_reward_allocations_available_at ON growth_reward_allocations(available_at)",
            "CREATE INDEX ix_growth_reward_allocations_wallet_transaction_id "
            "ON growth_reward_allocations(wallet_transaction_id)",
            "CREATE INDEX ix_growth_reward_allocations_created_by_admin_user_id "
            "ON growth_reward_allocations(created_by_admin_user_id)",
            "CREATE INDEX ix_growth_reward_allocations_allocated_at ON growth_reward_allocations(allocated_at)",
            "CREATE INDEX ix_growth_reward_allocations_reversed_at ON growth_reward_allocations(reversed_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE growth_reporting_daily_rollups (
                id TEXT PRIMARY KEY,
                report_date TEXT NOT NULL,
                report_family TEXT NOT NULL,
                metric_key TEXT NOT NULL,
                metric_unit TEXT NOT NULL DEFAULT 'count',
                dimension_key TEXT NOT NULL DEFAULT '',
                dimension_value TEXT NOT NULL DEFAULT '',
                metric_value NUMERIC NOT NULL,
                currency_code TEXT NOT NULL DEFAULT '',
                source_watermark_at TEXT,
                refreshed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (
                    report_date,
                    report_family,
                    metric_key,
                    dimension_key,
                    dimension_value,
                    currency_code
                )
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_growth_reporting_daily_rollups_report_date ON growth_reporting_daily_rollups(report_date)",
            "CREATE INDEX ix_growth_reporting_daily_rollups_report_family "
            "ON growth_reporting_daily_rollups(report_family)",
            "CREATE INDEX ix_growth_reporting_daily_rollups_metric_key ON growth_reporting_daily_rollups(metric_key)",
            "CREATE INDEX ix_growth_reporting_daily_rollups_source_watermark_at "
            "ON growth_reporting_daily_rollups(source_watermark_at)",
            "CREATE INDEX ix_growth_reporting_daily_rollups_refreshed_at "
            "ON growth_reporting_daily_rollups(refreshed_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE growth_reporting_refresh_runs (
                id TEXT PRIMARY KEY,
                trigger_kind TEXT NOT NULL,
                refresh_status TEXT NOT NULL,
                requested_window_days INTEGER NOT NULL,
                window_start TEXT NOT NULL,
                window_end TEXT NOT NULL,
                latest_rollup_date TEXT,
                rows_written INTEGER NOT NULL DEFAULT 0,
                families_updated TEXT NOT NULL DEFAULT '[]',
                error_message TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                refreshed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_growth_reporting_refresh_runs_trigger_kind ON growth_reporting_refresh_runs(trigger_kind)",
            "CREATE INDEX ix_growth_reporting_refresh_runs_refresh_status "
            "ON growth_reporting_refresh_runs(refresh_status)",
            "CREATE INDEX ix_growth_reporting_refresh_runs_window_start ON growth_reporting_refresh_runs(window_start)",
            "CREATE INDEX ix_growth_reporting_refresh_runs_window_end ON growth_reporting_refresh_runs(window_end)",
            "CREATE INDEX ix_growth_reporting_refresh_runs_refreshed_at ON growth_reporting_refresh_runs(refreshed_at)",
            "CREATE INDEX ix_growth_reporting_refresh_runs_created_at ON growth_reporting_refresh_runs(created_at)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE growth_reporting_subscriptions (
                id TEXT PRIMARY KEY,
                recipient_email TEXT NOT NULL,
                recipient_name TEXT,
                audience_key TEXT NOT NULL,
                delivery_channel TEXT NOT NULL DEFAULT 'email',
                cadence TEXT NOT NULL,
                report_window_days INTEGER NOT NULL DEFAULT 30,
                template_key TEXT NOT NULL DEFAULT 'cross_function_exec',
                template_locale TEXT NOT NULL DEFAULT 'en-EN',
                email_subject_prefix TEXT,
                title_override TEXT,
                recipient_domain_policy TEXT NOT NULL DEFAULT 'allow_any',
                allowed_recipient_domains TEXT NOT NULL DEFAULT '[]',
                suppressed_until TEXT,
                suppression_reason_code TEXT,
                governance_followup_status TEXT NOT NULL DEFAULT 'none',
                governance_followup_reason_code TEXT,
                governance_followup_opened_at TEXT,
                governance_followup_due_at TEXT,
                governance_followup_last_notified_at TEXT,
                governance_followup_resolved_at TEXT,
                governance_followup_resolution_code TEXT,
                subscription_status TEXT NOT NULL DEFAULT 'active',
                next_delivery_at TEXT NOT NULL,
                last_delivery_attempt_at TEXT,
                last_success_at TEXT,
                latest_delivery_status TEXT,
                latest_delivery_reason TEXT,
                created_by_admin_user_id TEXT,
                updated_by_admin_user_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY (updated_by_admin_user_id) REFERENCES admin_users(id)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_growth_reporting_subscriptions_recipient_email "
            "ON growth_reporting_subscriptions(recipient_email)",
            "CREATE INDEX ix_growth_reporting_subscriptions_audience_key "
            "ON growth_reporting_subscriptions(audience_key)",
            "CREATE INDEX ix_growth_reporting_subscriptions_delivery_channel "
            "ON growth_reporting_subscriptions(delivery_channel)",
            "CREATE INDEX ix_growth_reporting_subscriptions_cadence ON growth_reporting_subscriptions(cadence)",
            "CREATE INDEX ix_growth_reporting_subscriptions_subscription_status "
            "ON growth_reporting_subscriptions(subscription_status)",
            "CREATE INDEX ix_growth_reporting_subscriptions_next_delivery_at "
            "ON growth_reporting_subscriptions(next_delivery_at)",
            "CREATE INDEX ix_growth_reporting_subscriptions_suppressed_until "
            "ON growth_reporting_subscriptions(suppressed_until)",
            "CREATE INDEX ix_growth_reporting_subscriptions_governance_followup_status "
            "ON growth_reporting_subscriptions(governance_followup_status)",
            "CREATE INDEX ix_growth_reporting_subscriptions_governance_followup_reason_code "
            "ON growth_reporting_subscriptions(governance_followup_reason_code)",
            "CREATE INDEX ix_growth_reporting_subscriptions_governance_followup_due_at "
            "ON growth_reporting_subscriptions(governance_followup_due_at)",
            "CREATE INDEX ix_growth_reporting_subscriptions_latest_delivery_status "
            "ON growth_reporting_subscriptions(latest_delivery_status)",
            "CREATE INDEX ix_growth_reporting_subscriptions_created_by_admin_user_id "
            "ON growth_reporting_subscriptions(created_by_admin_user_id)",
            "CREATE INDEX ix_growth_reporting_subscriptions_updated_by_admin_user_id "
            "ON growth_reporting_subscriptions(updated_by_admin_user_id)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE growth_reporting_deliveries (
                id TEXT PRIMARY KEY,
                subscription_id TEXT NOT NULL,
                recipient_email TEXT NOT NULL,
                recipient_name TEXT,
                audience_key TEXT NOT NULL,
                delivery_channel TEXT NOT NULL DEFAULT 'email',
                cadence TEXT NOT NULL,
                report_window_days INTEGER NOT NULL,
                template_key TEXT NOT NULL DEFAULT 'cross_function_exec',
                template_locale TEXT NOT NULL DEFAULT 'en-EN',
                subject_line TEXT NOT NULL DEFAULT 'Growth reporting digest',
                title_line TEXT NOT NULL DEFAULT 'Growth reporting digest',
                recipient_domain_policy TEXT NOT NULL DEFAULT 'allow_any',
                allowed_recipient_domains TEXT NOT NULL DEFAULT '[]',
                delivery_status TEXT NOT NULL,
                status_reason TEXT,
                window_start TEXT NOT NULL,
                window_end TEXT NOT NULL,
                freshness_status TEXT NOT NULL DEFAULT 'fresh',
                artifact_checksum TEXT,
                artifact_payload TEXT NOT NULL DEFAULT '{}',
                provider_name TEXT,
                provider_message_id TEXT,
                failure_message TEXT,
                planned_at TEXT NOT NULL,
                started_at TEXT,
                delivered_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subscription_id) REFERENCES growth_reporting_subscriptions(id)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_growth_reporting_deliveries_subscription_id "
            "ON growth_reporting_deliveries(subscription_id)",
            "CREATE INDEX ix_growth_reporting_deliveries_recipient_email "
            "ON growth_reporting_deliveries(recipient_email)",
            "CREATE INDEX ix_growth_reporting_deliveries_audience_key ON growth_reporting_deliveries(audience_key)",
            "CREATE INDEX ix_growth_reporting_deliveries_template_key ON growth_reporting_deliveries(template_key)",
            "CREATE INDEX ix_growth_reporting_deliveries_delivery_channel "
            "ON growth_reporting_deliveries(delivery_channel)",
            "CREATE INDEX ix_growth_reporting_deliveries_cadence ON growth_reporting_deliveries(cadence)",
            "CREATE INDEX ix_growth_reporting_deliveries_delivery_status "
            "ON growth_reporting_deliveries(delivery_status)",
            "CREATE INDEX ix_growth_reporting_deliveries_window_start ON growth_reporting_deliveries(window_start)",
            "CREATE INDEX ix_growth_reporting_deliveries_window_end ON growth_reporting_deliveries(window_end)",
            "CREATE INDEX ix_growth_reporting_deliveries_planned_at ON growth_reporting_deliveries(planned_at)",
            "CREATE INDEX ix_growth_reporting_deliveries_delivered_at ON growth_reporting_deliveries(delivered_at)",
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
                identity_scope TEXT NOT NULL DEFAULT 'account',
                subscription_key TEXT,
                provider_subject_ref TEXT,
                identity_status TEXT NOT NULL DEFAULT 'active',
                service_context TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_account_id) REFERENCES mobile_users(id),
                FOREIGN KEY (auth_realm_id) REFERENCES auth_realms(id),
                FOREIGN KEY (source_order_id) REFERENCES orders(id),
                FOREIGN KEY (origin_storefront_id) REFERENCES storefronts(id),
                UNIQUE (customer_account_id, auth_realm_id, provider_name, identity_scope, subscription_key)
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
            "CREATE INDEX ix_service_identities_identity_scope ON service_identities(identity_scope)",
            "CREATE INDEX ix_service_identities_subscription_key ON service_identities(subscription_key)",
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
            "CREATE INDEX ix_device_credentials_provider_credential_ref ON device_credentials(provider_credential_ref)",
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
            "CREATE INDEX ix_access_delivery_channels_last_delivered_at ON access_delivery_channels(last_delivered_at)",
            "CREATE INDEX ix_access_delivery_channels_last_accessed_at ON access_delivery_channels(last_accessed_at)",
            "CREATE INDEX ix_access_delivery_channels_archived_at ON access_delivery_channels(archived_at)",
            "CREATE INDEX ix_access_delivery_channels_archived_by_admin_user_id "
            "ON access_delivery_channels(archived_by_admin_user_id)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE webhook_logs (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                event_type TEXT,
                payload TEXT NOT NULL,
                signature TEXT,
                is_valid BOOLEAN,
                processed_at TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_webhook_logs_source ON webhook_logs(source)",
            "CREATE INDEX ix_webhook_logs_created_at ON webhook_logs(created_at)",
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
            "CREATE INDEX ix_outbox_publications_publication_status ON outbox_publications(publication_status)",
            "CREATE INDEX ix_outbox_publications_lease_owner ON outbox_publications(lease_owner)",
            "CREATE INDEX ix_outbox_publications_leased_until ON outbox_publications(leased_until)",
        ):
            conn.exec_driver_sql(index_sql)
        conn.exec_driver_sql(
            """
            CREATE TABLE outbox_consumer_receipts (
                id TEXT PRIMARY KEY,
                consumer_key TEXT NOT NULL,
                event_key TEXT NOT NULL,
                event_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'processed',
                metadata_payload TEXT NOT NULL DEFAULT '{}',
                processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (consumer_key, event_key)
            )
            """
        )
        for index_sql in (
            "CREATE INDEX ix_outbox_consumer_receipts_consumer_key ON outbox_consumer_receipts(consumer_key)",
            "CREATE INDEX ix_outbox_consumer_receipts_event_key ON outbox_consumer_receipts(event_key)",
            "CREATE INDEX ix_outbox_consumer_receipts_event_name ON outbox_consumer_receipts(event_name)",
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
    engine = _REALM_TEST_ENGINES.pop(path, None)
    if engine is not None:
        engine.dispose()
    path.unlink(missing_ok=True)
