"""Check for anomalies and send alerts."""

import json
from datetime import datetime, timezone

import structlog

from src.broker import broker
from src.services.redis_client import get_redis_client
from src.services.telegram_client import TelegramClient
from src.utils.formatting import anomaly_alert

logger = structlog.get_logger(__name__)

# Anomaly thresholds
SERVER_OFFLINE_SECONDS = 300  # 5 minutes = CRITICAL
ERROR_RATE_THRESHOLD = 5.0  # 5% = WARNING
QUEUE_DEPTH_THRESHOLD = 500  # = WARNING
PAYMENT_FAILURE_THRESHOLD = 10.0  # 10% = CRITICAL


@broker.task(task_name="check_anomalies", queue="reports")
async def check_anomalies() -> dict:
    """Check for anomalies and send alerts.

    Monitors system health metrics and sends Telegram alerts when thresholds
    are exceeded:
    - Server offline > 5 minutes = CRITICAL
    - Error rate > 5% = WARNING
    - Queue depth > 500 = WARNING

    Returns:
        Dictionary with alerts_sent count
    """
    redis = get_redis_client()
    alerts_sent = 0

    try:
        async with TelegramClient() as tg:
            # Check server health (offline duration)
            cursor = 0
            while True:
                cursor, keys = await redis.scan(cursor, match="cybervpn:health:*:current", count=100)
                for key in keys:
                    data = await redis.get(key)
                    if not data:
                        continue

                    try:
                        health = json.loads(data)
                        is_online = health.get("is_online", True)
                        if not is_online:
                            offline_since = health.get("offline_since") or health.get("last_seen")
                            node_name = health.get("name", "unknown")
                            if offline_since:
                                try:
                                    offline_duration = int(datetime.now(timezone.utc).timestamp()) - int(offline_since)
                                except (TypeError, ValueError):
                                    offline_duration = 0
                            else:
                                offline_duration = 0

                            if offline_duration >= SERVER_OFFLINE_SECONDS:
                                msg = anomaly_alert(
                                    metric=f"Server: {node_name}",
                                    current_value=f"OFFLINE {offline_duration}s",
                                    threshold=f"> {SERVER_OFFLINE_SECONDS}s",
                                    severity="critical",
                                )
                                await tg.send_admin_alert(msg, severity="critical")
                                alerts_sent += 1
                    except json.JSONDecodeError:
                        pass

                if cursor == 0:
                    break

            # Check error rate (would need error counters)
            error_rate_key = "cybervpn:metrics:error_rate"
            error_rate_data = await redis.get(error_rate_key)
            if error_rate_data:
                try:
                    error_rate = float(error_rate_data)
                    if error_rate > ERROR_RATE_THRESHOLD:
                        msg = anomaly_alert(
                            metric="Error Rate",
                            current_value=f"{error_rate:.2f}%",
                            threshold=f"< {ERROR_RATE_THRESHOLD}%",
                            severity="warning",
                        )
                        await tg.send_admin_alert(msg, severity="warning")
                        alerts_sent += 1
                except (ValueError, TypeError):
                    pass

            # Check queue depth (TaskIQ queue lengths)
            queue_depth_key = "cybervpn:metrics:queue_depth"
            queue_depth_data = await redis.get(queue_depth_key)
            if queue_depth_data:
                try:
                    queue_depth = int(queue_depth_data)
                    if queue_depth > QUEUE_DEPTH_THRESHOLD:
                        msg = anomaly_alert(
                            metric="Queue Depth",
                            current_value=str(queue_depth),
                            threshold=f"< {QUEUE_DEPTH_THRESHOLD}",
                            severity="warning",
                        )
                        await tg.send_admin_alert(msg, severity="warning")
                        alerts_sent += 1
                except (ValueError, TypeError):
                    pass

            # Check payment failure rate
            payment_failure_key = "cybervpn:metrics:payment_failure_rate"
            payment_failure_data = await redis.get(payment_failure_key)
            if payment_failure_data:
                try:
                    failure_rate = float(payment_failure_data)
                    if failure_rate > PAYMENT_FAILURE_THRESHOLD:
                        msg = anomaly_alert(
                            metric="Payment Failure Rate",
                            current_value=f"{failure_rate:.2f}%",
                            threshold=f"< {PAYMENT_FAILURE_THRESHOLD}%",
                            severity="critical",
                        )
                        await tg.send_admin_alert(msg, severity="critical")
                        alerts_sent += 1
                except (ValueError, TypeError):
                    pass

        logger.info("anomaly_check_complete", alerts_sent=alerts_sent)

    except Exception as e:
        logger.exception("anomaly_check_failed", error=str(e))
        raise
    finally:
        await redis.aclose()

    return {"alerts_sent": alerts_sent}
