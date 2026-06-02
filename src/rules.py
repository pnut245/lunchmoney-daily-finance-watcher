"""Starter anomaly and rule checks for Lunch Money snapshots."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from . import storage


def load_rules(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def run_checks(db_path: Path, config: dict[str, Any], run_date: date) -> tuple[int, list[dict[str, Any]]]:
    storage.init_db(db_path)
    run_id = storage.create_rule_run(db_path, run_date, config)
    hits: list[dict[str, Any]] = []

    with storage.connect(db_path) as conn:
        recent_days = int(config.get("checks", {}).get("recent_transaction_days", 3))
        recent_start = run_date - timedelta(days=max(recent_days - 1, 0))
        recent_transactions = _transactions_between(conn, recent_start, run_date)

        hits.extend(_high_transaction_hits(recent_transactions, config))
        hits.extend(_new_merchant_hits(conn, recent_transactions, recent_start, config))
        hits.extend(_duplicate_charge_hits(conn, recent_start, run_date, config))
        hits.extend(_uncategorized_hits(recent_transactions, config))
        hits.extend(_recurring_amount_change_hits(conn, config))
        hits.extend(_unusual_daily_spend_hits(conn, run_date, config))
        hits.extend(_category_budget_pacing_hits(conn, run_date, config))

    storage.insert_rule_hits(db_path, run_id, hits)
    return run_id, hits


def _high_transaction_hits(
    transactions: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    rule = config.get("checks", {}).get("high_transaction", {})
    if not rule.get("enabled", True):
        return []
    threshold = float(rule.get("threshold", 100.0))
    hits = []
    for txn in transactions:
        amount = _spend_amount(txn)
        if amount >= threshold:
            hits.append(
                _hit(
                    "high_transaction",
                    "review",
                    f"Transaction above ${threshold:,.2f}: {_payee(txn)}",
                    txn,
                    {"threshold": threshold, "category": txn.get("category_name")},
                )
            )
    return hits


def _new_merchant_hits(
    conn: Any,
    recent_transactions: list[dict[str, Any]],
    recent_start: date,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    rule = config.get("checks", {}).get("new_merchant", {})
    if not rule.get("enabled", True):
        return []
    ignored = {_normalize_payee(payee) for payee in rule.get("ignore_merchants", [])}
    known = {
        _normalize_payee(row["payee"])
        for row in conn.execute(
            "SELECT DISTINCT payee FROM transactions WHERE date < ? AND payee IS NOT NULL",
            (recent_start.isoformat(),),
        )
        if _normalize_payee(row["payee"])
    }
    if not known:
        return []

    seen_in_report: set[str] = set()
    hits = []
    for txn in recent_transactions:
        payee_key = _normalize_payee(txn.get("payee"))
        if not payee_key or payee_key in ignored or payee_key in known or payee_key in seen_in_report:
            continue
        seen_in_report.add(payee_key)
        hits.append(
            _hit(
                "new_merchant",
                "review",
                f"New merchant/payee: {_payee(txn)}",
                txn,
                {"first_seen_in_recent_window": True},
            )
        )
    return hits


def _duplicate_charge_hits(
    conn: Any, recent_start: date, run_date: date, config: dict[str, Any]
) -> list[dict[str, Any]]:
    rule = config.get("checks", {}).get("duplicate_charge", {})
    if not rule.get("enabled", True):
        return []
    window_days = int(rule.get("window_days", 3))
    tolerance = float(rule.get("amount_tolerance", 0.01))
    search_start = recent_start - timedelta(days=window_days)
    candidates = [
        row_to_dict(row)
        for row in conn.execute(
            """
            SELECT t.*, c.name AS category_name, c.is_income, c.exclude_from_totals
            FROM transactions t
            LEFT JOIN categories c ON c.id = t.category_id
            WHERE t.date BETWEEN ? AND ?
            ORDER BY t.date, t.id
            """,
            (search_start.isoformat(), run_date.isoformat()),
        )
        if _spend_amount(row) > 0 and _normalize_payee(row["payee"])
    ]

    grouped: dict[str, list[list[dict[str, Any]]]] = defaultdict(list)
    for txn in candidates:
        key = _normalize_payee(txn.get("payee"))
        placed = False
        for group in grouped[key]:
            if abs(_spend_amount(txn) - _spend_amount(group[0])) <= tolerance:
                group.append(txn)
                placed = True
                break
        if not placed:
            grouped[key].append([txn])

    hits = []
    for groups in grouped.values():
        for group in groups:
            if len(group) < 2:
                continue
            dates = [_parse_date(txn["date"]) for txn in group]
            if (max(dates) - min(dates)).days > window_days:
                continue
            if not any(_parse_date(txn["date"]) >= recent_start for txn in group):
                continue
            ids = [str(txn["id"]) for txn in group]
            amount = _spend_amount(group[0])
            hits.append(
                {
                    "rule_name": "duplicate_charge",
                    "severity": "review",
                    "title": f"Possible duplicate charge: {_payee(group[0])} ${amount:,.2f}",
                    "entity_type": "transaction_group",
                    "entity_id": ",".join(ids),
                    "date": max(dates).isoformat(),
                    "amount": amount,
                    "payee": _payee(group[0]),
                    "details": {
                        "transaction_ids": ids,
                        "dates": [txn["date"] for txn in group],
                        "window_days": window_days,
                        "amount_tolerance": tolerance,
                    },
                }
            )
    return hits


def _uncategorized_hits(
    transactions: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    rule = config.get("checks", {}).get("uncategorized", {})
    if not rule.get("enabled", True):
        return []
    hits = []
    for txn in transactions:
        if _spend_amount(txn) <= 0:
            continue
        if txn.get("category_id") is None:
            hits.append(
                _hit(
                    "uncategorized",
                    "review",
                    f"Uncategorized transaction: {_payee(txn)}",
                    txn,
                    {"status": txn.get("status")},
                )
            )
    return hits


def _recurring_amount_change_hits(conn: Any, config: dict[str, Any]) -> list[dict[str, Any]]:
    rule = config.get("checks", {}).get("recurring_amount_change", {})
    if not rule.get("enabled", True):
        return []
    tolerance = float(rule.get("amount_tolerance", 0.5))
    rows = conn.execute(
        """
        SELECT DISTINCT snapshot_date
        FROM recurring_item_snapshots
        ORDER BY snapshot_date DESC
        LIMIT 2
        """
    ).fetchall()
    if len(rows) < 2:
        return []
    latest_date = rows[0]["snapshot_date"]
    previous_date = rows[1]["snapshot_date"]
    changes = conn.execute(
        """
        SELECT
            latest.id,
            latest.payee,
            latest.amount AS latest_amount,
            previous.amount AS previous_amount,
            latest.currency,
            latest.category_id
        FROM recurring_item_snapshots latest
        JOIN recurring_item_snapshots previous
            ON previous.id = latest.id
        WHERE latest.snapshot_date = ?
          AND previous.snapshot_date = ?
          AND latest.amount IS NOT NULL
          AND previous.amount IS NOT NULL
          AND ABS(latest.amount - previous.amount) > ?
        """,
        (latest_date, previous_date, tolerance),
    ).fetchall()

    hits = []
    for row in changes:
        hits.append(
            {
                "rule_name": "recurring_amount_change",
                "severity": "review",
                "title": (
                    f"Recurring amount changed: {row['payee'] or row['id']} "
                    f"${row['previous_amount']:,.2f} -> ${row['latest_amount']:,.2f}"
                ),
                "entity_type": "recurring_item",
                "entity_id": str(row["id"]),
                "date": latest_date,
                "amount": row["latest_amount"],
                "payee": row["payee"],
                "details": {
                    "previous_snapshot_date": previous_date,
                    "latest_snapshot_date": latest_date,
                    "previous_amount": row["previous_amount"],
                    "latest_amount": row["latest_amount"],
                    "currency": row["currency"],
                    "category_id": row["category_id"],
                    "tolerance": tolerance,
                },
            }
        )
    return hits


def _unusual_daily_spend_hits(conn: Any, run_date: date, config: dict[str, Any]) -> list[dict[str, Any]]:
    rule = config.get("checks", {}).get("unusual_daily_spend", {})
    if not rule.get("enabled", True):
        return []
    current_spend = _daily_spend(conn, run_date)
    minimum_spend = float(rule.get("minimum_spend", 150.0))
    multiplier = float(rule.get("multiplier", 2.0))
    hits = []
    for window in rule.get("windows", [30, 90]):
        window = int(window)
        if window <= 0:
            continue
        trailing_start = run_date - timedelta(days=window)
        trailing_end = run_date - timedelta(days=1)
        trailing_spend = _spend_between(conn, trailing_start, trailing_end)
        average = trailing_spend / window
        threshold = max(minimum_spend, average * multiplier)
        if average > 0 and current_spend > threshold:
            hits.append(
                {
                    "rule_name": "unusual_daily_spend",
                    "severity": "review",
                    "title": f"Daily spend is unusually high vs trailing {window}-day average",
                    "entity_type": "day",
                    "entity_id": run_date.isoformat(),
                    "date": run_date.isoformat(),
                    "amount": current_spend,
                    "payee": None,
                    "details": {
                        "current_spend": round(current_spend, 2),
                        "trailing_days": window,
                        "trailing_average": round(average, 2),
                        "threshold": round(threshold, 2),
                        "multiplier": multiplier,
                    },
                }
            )
    return hits


def _category_budget_pacing_hits(conn: Any, run_date: date, config: dict[str, Any]) -> list[dict[str, Any]]:
    rule = config.get("checks", {}).get("category_budget_pacing", {})
    if not rule.get("enabled", True):
        return []
    latest = conn.execute(
        "SELECT MAX(snapshot_date) AS snapshot_date FROM budget_summary_categories"
    ).fetchone()
    if not latest or not latest["snapshot_date"]:
        return []
    threshold_ratio = float(rule.get("threshold_ratio", 1.15))
    minimum_overspend = float(rule.get("minimum_overspend", 10.0))
    rows = conn.execute(
        """
        SELECT b.*, c.name AS category_name
        FROM budget_summary_categories b
        LEFT JOIN categories c ON c.id = b.category_id
        WHERE b.snapshot_date = ?
          AND b.budgeted IS NOT NULL
          AND b.budgeted > 0
          AND b.start_date IS NOT NULL
          AND b.end_date IS NOT NULL
        """,
        (latest["snapshot_date"],),
    ).fetchall()

    hits = []
    for row in rows:
        start = _parse_date(row["start_date"])
        end = _parse_date(row["end_date"])
        if not (start <= run_date <= end):
            continue
        period_days = max((end - start).days + 1, 1)
        elapsed_days = max((run_date - start).days + 1, 1)
        expected_ratio = min(elapsed_days / period_days, 1.0)
        spending = max(float(row["spending"] or 0.0), 0.0)
        budgeted = float(row["budgeted"])
        actual_ratio = spending / budgeted
        expected_spend = budgeted * expected_ratio
        overspend_vs_pace = spending - expected_spend
        if actual_ratio > expected_ratio * threshold_ratio and overspend_vs_pace >= minimum_overspend:
            category_name = row["category_name"] or f"Category {row['category_id']}"
            hits.append(
                {
                    "rule_name": "category_budget_pacing",
                    "severity": "review",
                    "title": f"Budget pacing high: {category_name}",
                    "entity_type": "category",
                    "entity_id": str(row["category_id"]),
                    "date": run_date.isoformat(),
                    "amount": spending,
                    "payee": None,
                    "details": {
                        "category_name": category_name,
                        "budgeted": round(budgeted, 2),
                        "spending": round(spending, 2),
                        "actual_ratio": round(actual_ratio, 3),
                        "expected_ratio": round(expected_ratio, 3),
                        "threshold_ratio": threshold_ratio,
                        "overspend_vs_pace": round(overspend_vs_pace, 2),
                    },
                }
            )
    return hits


def _transactions_between(conn: Any, start: date, end: date) -> list[dict[str, Any]]:
    return [
        row_to_dict(row)
        for row in conn.execute(
            """
            SELECT t.*, c.name AS category_name, c.is_income, c.exclude_from_totals
            FROM transactions t
            LEFT JOIN categories c ON c.id = t.category_id
            WHERE t.date BETWEEN ? AND ?
            ORDER BY t.date DESC, t.id DESC
            """,
            (start.isoformat(), end.isoformat()),
        )
    ]


def _daily_spend(conn: Any, day: date) -> float:
    return _spend_between(conn, day, day)


def _spend_between(conn: Any, start: date, end: date) -> float:
    row = conn.execute(
        """
        SELECT COALESCE(SUM(t.amount), 0) AS spend
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND t.amount > 0
          AND COALESCE(c.is_income, 0) = 0
          AND COALESCE(c.exclude_from_totals, 0) = 0
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchone()
    return float(row["spend"] or 0.0)


def _hit(
    rule_name: str,
    severity: str,
    title: str,
    txn: dict[str, Any],
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "rule_name": rule_name,
        "severity": severity,
        "title": title,
        "entity_type": "transaction",
        "entity_id": str(txn["id"]),
        "date": txn.get("date"),
        "amount": _spend_amount(txn),
        "payee": _payee(txn),
        "details": {"transaction_id": txn["id"], **details},
    }


def _spend_amount(txn: Any) -> float:
    amount = float(txn["amount"] if isinstance(txn, dict) else txn["amount"])
    is_income = int(txn["is_income"] or 0) if "is_income" in txn.keys() else 0
    exclude = int(txn["exclude_from_totals"] or 0) if "exclude_from_totals" in txn.keys() else 0
    if is_income or exclude or amount <= 0:
        return 0.0
    return amount


def _payee(txn: dict[str, Any]) -> str:
    return str(txn.get("payee") or txn.get("original_name") or "Unknown payee")


def _normalize_payee(payee: Any) -> str:
    value = str(payee or "").lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def row_to_dict(row: Any) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def summarize_hits(hits: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(hit["rule_name"] for hit in hits))


def details_from_row(row: Any) -> dict[str, Any]:
    try:
        return json.loads(row["details_json"] or "{}")
    except json.JSONDecodeError:
        return {}
