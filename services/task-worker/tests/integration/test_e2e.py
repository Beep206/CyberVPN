"""End-to-end integration smoke tests.

This module provides high-level smoke tests that verify the overall integrity
of the task worker without requiring real infrastructure (Redis, PostgreSQL, etc.).

Tests verify:
- All task modules can be imported without errors
- All task functions are properly decorated with @broker.task
- Task metadata is properly configured

This is NOT a full E2E test with real infrastructure - it's a smoke test
that validates the codebase structure and configuration.
"""

import importlib
import inspect
import pytest

from src.utils.constants import (
    QUEUE_ANALYTICS,
    QUEUE_BULK,
    QUEUE_CLEANUP,
    QUEUE_MONITORING,
    QUEUE_NOTIFICATIONS,
    QUEUE_PAYMENTS,
    QUEUE_REPORTS,
    QUEUE_SUBSCRIPTIONS,
    QUEUE_SYNC,
)


@pytest.mark.integration
class TestE2EIntegration:
    """End-to-end smoke tests for task worker integration."""

    def test_all_task_modules_can_be_imported(self):
        """Verify all task modules can be imported without errors."""
        task_modules = [
            # Notifications
            "src.tasks.notifications.process_queue",
            "src.tasks.notifications.send_notification",
            "src.tasks.notifications.broadcast",
            # Monitoring
            "src.tasks.monitoring.health_check",
            "src.tasks.monitoring.services_health",
            "src.tasks.monitoring.bandwidth",
            "src.tasks.monitoring.queue_depth",
            "src.tasks.monitoring.connection_pools",
            "src.tasks.monitoring.memory",
            # Subscriptions
            "src.tasks.subscriptions.check_expiring",
            "src.tasks.subscriptions.disable_expired",
            "src.tasks.subscriptions.auto_renew",
            "src.tasks.subscriptions.reset_traffic",
            # Analytics
            "src.tasks.analytics.daily_stats",
            "src.tasks.analytics.financial_stats",
            "src.tasks.analytics.hourly_bandwidth",
            "src.tasks.analytics.realtime_metrics",
            # Payments
            "src.tasks.payments.verify_pending",
            "src.tasks.payments.retry_webhooks",
            "src.tasks.payments.process_completion",
            # Cleanup
            "src.tasks.cleanup.cleanup_old_records",
            "src.tasks.cleanup.tokens",
            "src.tasks.cleanup.audit_logs",
            "src.tasks.cleanup.webhook_logs",
            "src.tasks.cleanup.notifications",
            "src.tasks.cleanup.cache",
            "src.tasks.cleanup.export_files",
            # Sync
            "src.tasks.sync.sync_nodes",
            "src.tasks.sync.geolocations",
            "src.tasks.sync.user_stats",
            "src.tasks.sync.node_configs",
            # Reports
            "src.tasks.reports.daily_report",
            "src.tasks.reports.weekly_report",
            "src.tasks.reports.anomaly_alert",
            # Bulk
            "src.tasks.bulk.bulk_operations",
            "src.tasks.bulk.user_operations",
            "src.tasks.bulk.export",
            "src.tasks.bulk.broadcast",
        ]

        # Attempt to import each module
        for module_path in task_modules:
            try:
                importlib.import_module(module_path)
            except Exception as e:
                pytest.fail(f"Failed to import {module_path}: {e}")

    def test_all_task_functions_are_decorated(self):
        """Verify all task functions are properly decorated with @broker.task."""
        # Import a sample of key task functions directly
        from src.tasks.notifications.process_queue import process_notification_queue
        from src.tasks.monitoring.health_check import check_server_health
        from src.tasks.subscriptions.check_expiring import check_expiring_subscriptions
        from src.tasks.analytics.daily_stats import aggregate_daily_stats
        from src.tasks.payments.verify_pending import verify_pending_payments
        from src.tasks.cleanup.cleanup_old_records import cleanup_old_records
        from src.tasks.sync.sync_nodes import sync_node_configs
        from src.tasks.reports.daily_report import send_daily_report

        # List of task functions
        task_funcs = [
            process_notification_queue,
            check_server_health,
            check_expiring_subscriptions,
            aggregate_daily_stats,
            verify_pending_payments,
            cleanup_old_records,
            sync_node_configs,
            send_daily_report,
        ]

        for task_func in task_funcs:
            # Verify it's a TaskIQ task (has kicker attribute)
            assert hasattr(task_func, "kicker"), f"{task_func} should be a TaskIQ task"

            # Verify it has task_name
            assert hasattr(task_func, "task_name"), f"{task_func} should have task_name attribute"

    def test_broker_configuration_is_complete(self):
        """Verify broker has all required configuration."""
        from src.broker import broker, scheduler, result_backend, schedule_source

        # Broker should be configured
        assert broker is not None
        assert broker.result_backend is not None

        # Scheduler should be configured
        assert scheduler is not None
        assert len(scheduler.sources) > 0

        # Result backend should be configured
        assert result_backend is not None

        # Schedule source should be configured
        assert schedule_source is not None

    def test_middleware_configuration_is_complete(self):
        """Verify all middleware classes can be instantiated."""
        from src.middleware import (
            ErrorHandlerMiddleware,
            LoggingMiddleware,
            MetricsMiddleware,
            RetryMiddleware,
        )

        # Verify middleware can be instantiated
        logging_mw = LoggingMiddleware()
        metrics_mw = MetricsMiddleware()
        error_mw = ErrorHandlerMiddleware()
        retry_mw = RetryMiddleware()

        # Verify they have required methods
        assert hasattr(logging_mw, "pre_execute")
        assert hasattr(logging_mw, "post_execute")
        assert hasattr(metrics_mw, "pre_execute")
        assert hasattr(metrics_mw, "post_execute")
        assert hasattr(error_mw, "post_execute")
        assert hasattr(retry_mw, "post_execute")

    def test_services_can_be_imported(self):
        """Verify all service modules can be imported."""
        service_modules = [
            "src.services.telegram_client",
            "src.services.cryptobot_client",
            "src.services.remnawave_client",
            "src.services.cache_service",
            "src.services.redis_client",
        ]

        for module_path in service_modules:
            try:
                importlib.import_module(module_path)
            except Exception as e:
                pytest.fail(f"Failed to import {module_path}: {e}")

    def test_database_models_can_be_imported(self):
        """Verify all database models can be imported."""
        model_modules = [
            "src.models.notification_queue",
            "src.models.payment",
            "src.models.subscription_plan",
            "src.models.server_geolocation",
            "src.models.audit_log",
            "src.models.webhook_log",
            "src.models.refresh_token",
        ]

        for module_path in model_modules:
            try:
                module = importlib.import_module(module_path)
                # Verify the model has a proper Base class
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and name.endswith("Model"):
                        # Should have __tablename__ attribute
                        assert hasattr(obj, "__tablename__"), f"{name} should have __tablename__"
            except Exception as e:
                pytest.fail(f"Failed to import {module_path}: {e}")

    def test_config_can_be_loaded(self):
        """Verify configuration can be loaded without errors."""
        from src.config import get_settings

        settings = get_settings()

        # Verify key settings exist
        assert hasattr(settings, "redis_url")
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "environment")
        assert hasattr(settings, "worker_concurrency")
        assert hasattr(settings, "metrics_port")

    def test_constants_are_properly_defined(self):
        """Verify all required constants are defined."""
        from src.utils import constants

        # Verify queue names
        assert hasattr(constants, "QUEUE_NOTIFICATIONS")
        assert hasattr(constants, "QUEUE_MONITORING")
        assert hasattr(constants, "QUEUE_SUBSCRIPTIONS")
        assert hasattr(constants, "QUEUE_ANALYTICS")
        assert hasattr(constants, "QUEUE_PAYMENTS")
        assert hasattr(constants, "QUEUE_CLEANUP")
        assert hasattr(constants, "QUEUE_SYNC")
        assert hasattr(constants, "QUEUE_REPORTS")
        assert hasattr(constants, "QUEUE_BULK")

        # Verify retry policies
        assert hasattr(constants, "RETRY_POLICIES")
        assert isinstance(constants.RETRY_POLICIES, dict)

        # Verify schedule constants
        assert hasattr(constants, "SCHEDULE_NOTIFICATION_QUEUE")
        assert hasattr(constants, "SCHEDULE_HEALTH_CHECK")

    def test_metrics_are_properly_defined(self):
        """Verify Prometheus metrics are properly defined."""
        from src.metrics import (
            TASK_DURATION,
            TASK_TOTAL,
            TASK_IN_PROGRESS,
            QUEUE_DEPTH,
            WORKER_INFO,
            EXTERNAL_REQUEST_TOTAL,
            EXTERNAL_REQUEST_DURATION,
        )

        # Verify metrics exist and have proper types
        assert TASK_DURATION is not None
        assert TASK_TOTAL is not None
        assert TASK_IN_PROGRESS is not None
        assert QUEUE_DEPTH is not None
        assert WORKER_INFO is not None
        assert EXTERNAL_REQUEST_TOTAL is not None
        assert EXTERNAL_REQUEST_DURATION is not None

    def test_logging_is_configured(self):
        """Verify logging is properly configured."""
        from src.logging_config import configure_logging
        import structlog

        # Should not raise any errors
        configure_logging()

        # Should be able to get a logger
        logger = structlog.get_logger(__name__)
        assert logger is not None

    def test_types_module_exists(self):
        """Verify types module with type aliases exists."""
        from src.types import TaskResult, UserId, NodeId, PaymentId

        # Verify type aliases are defined
        assert TaskResult is not None
        assert UserId is not None
        assert NodeId is not None
        assert PaymentId is not None

    def test_py_typed_marker_exists(self):
        """Verify py.typed marker file exists for PEP 561 compliance."""
        import os
        from pathlib import Path

        src_dir = Path(__file__).parent.parent.parent / "src"
        py_typed_file = src_dir / "py.typed"

        assert py_typed_file.exists(), "py.typed marker file should exist"
