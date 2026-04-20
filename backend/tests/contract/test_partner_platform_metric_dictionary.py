from pathlib import Path


def _read_metric_dictionary() -> str:
    repo_root = Path(__file__).resolve().parents[3]
    return (repo_root / "docs/api/partner-platform-metric-dictionary.md").read_text(encoding="utf-8")


def test_metric_dictionary_contains_canonical_metric_names() -> None:
    content = _read_metric_dictionary()

    for metric_name in (
        "paid_conversion",
        "qualifying_first_payment",
        "refund_rate",
        "chargeback_rate",
        "d30_paid_retention",
        "earnings_available",
        "payout_liability",
        "net_paid_orders_90d",
    ):
        assert metric_name in content


def test_metric_dictionary_contains_reconciliation_vocabulary() -> None:
    content = _read_metric_dictionary()

    for term in (
        "order_total",
        "reward_total",
        "statement_total",
        "payout_total",
    ):
        assert term in content
