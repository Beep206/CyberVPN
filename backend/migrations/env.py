import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.config.settings import settings
from src.infrastructure.database.session import Base

# Import all models so Alembic can detect them
from src.infrastructure.database.models.admin_user_model import AdminUserModel  # noqa: F401
from src.infrastructure.database.models.oauth_account_model import OAuthAccount  # noqa: F401
from src.infrastructure.database.models.refresh_token_model import RefreshToken  # noqa: F401
from src.infrastructure.database.models.payment_model import PaymentModel  # noqa: F401
from src.infrastructure.database.models.webhook_log_model import WebhookLog  # noqa: F401
from src.infrastructure.database.models.audit_log_model import AuditLog  # noqa: F401
from src.infrastructure.database.models.server_geolocation_model import ServerGeolocation  # noqa: F401
from src.infrastructure.database.models.notification_queue_model import NotificationQueue  # noqa: F401
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
