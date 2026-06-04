"""One Number Today calculation and ledger helpers."""

from __future__ import annotations

import json
from calendar import monthrange
from datetime import date
from pathlib import Path
from typing import Any

from . import storage


DEFAULT_EXCLUDED_CATEGORIES = [
    "Rent",
    "Mortgage",
    "Insurance",
    "Utilities",
    "Taxes",
    "Transfers",
    "Savings",
    "Income",
]
DEFAULT_EXCLUDED_KEYWORDS = [
    "rent",
    "mortgage",
    "insurance",
    "utilities",
    "taxes",
    "transfer",
    "deposit",
    "loan payment",
    "credit card payment",
    "savings transfer",
    "reimbursement",
]
DEFAULT_PRESETS = [5, 25, 55, 111]


def settings_from_config(budget_config: dict[str, Any]) -> dict[str, Any]:
    raw = budget_config.get("one_number", {}) or {}
    daily_allowance = _as_float(raw.get("daily_allowance"))
    presets = [
        value
        for value in (_as_float(item) for item in raw.get("preset_amounts", DEFAULT_PRESETS))
        if value is not None and value > 0
    ]
    excluded_categories = _clean_strings(
        raw.get("excluded_categories", DEFAULT_EXCLUDED_CATEGORIES)
    )
    excluded_payees = _clean_strings(raw.get("excluded_payees", []))
    excluded_keywords = _clean_strings(raw.get("excluded_keywords", DEFAULT_EXCLUDED_KEYWORDS))
    return {
        "enabled": bool(raw.get("enabled", True)),
        "daily_allowance": daily_allowance if daily_allowance is not None else 55.0,
        "preset_amounts": presets or DEFAULT_PRESETS,
        "excluded_categories": excluded_categories or DEFAULT_EXCLUDED_CATEGORIES,
        "excluded_payees": excluded_payees,
        "excluded_keywords": excluded_keywords or DEFAULT_EXCLUDED_KEYWORDS,
        "reset_day": int(raw.get("reset_day", 1) or 1),
        "reset_time": str(raw.get("reset_time", "00:00") or "00:00"),
    }


def build_state(
    db_path: Path,
    budget_config: dict[str, Any],
    run_date: date,
    *,
    last_updated: str | None = None,
) -> dict[str, Any]:
    settings = settings_from_config(budget_config)
    with storage.connect(db_path) as conn:
        today_spend = discretionary_spend_for_range(conn, run_date, run_date, settings)

    daily_allowance = float(settings["daily_allowance"])
    remaining_today = round(daily_allowance - today_spend, 2)
    return {
        "daily_allowance": _round_money(daily_allowance),
        "today_discretionary_spend": _round_money(today_spend),
        "spent_today": _round_money(today_spend),
        "remaining_today": _round_money(remaining_today),
        "is_negative": remaining_today < 0,
        "state": "negative" if remaining_today < 0 else "positive",
        "last_updated": last_updated or run_date.isoformat(),
        "updated_at": last_updated or run_date.isoformat(),
        "excluded_categories": settings["excluded_categories"],
        "excluded_payees": settings["excluded_payees"],
        "excluded_keywords": settings["excluded_keywords"],
        "reset_day": settings["reset_day"],
        "reset_time": settings["reset_time"],
    }


def discretionary_spend_for_range(
    conn: Any,
    start: date,
    end: date,
    settings: dict[str, Any],
) -> float:
    rows = conn.execute(
        """
        SELECT t.amount, t.payee, t.original_name, COALESCE(c.name, '') AS category_name
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND COALESCE(t.is_pending, 0) = 0
          AND t.amount > 0
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    excluded_categories = _normalized_set(settings.get("excluded_categories", []))
    excluded_payees = _normalized_set(settings.get("excluded_payees", []))
    excluded_keywords = _normalized_set(settings.get("excluded_keywords", []))
    total = 0.0
    for row in rows:
        category = _normalize(row["category_name"])
        payee = _normalize(row["payee"] or row["original_name"] or "")
        if category and category in excluded_categories:
            continue
        if payee and payee in excluded_payees:
            continue
        if excluded_keywords and any(keyword in category or keyword in payee for keyword in excluded_keywords):
            continue
        total += float(row["amount"] or 0.0)
    return round(total, 2)


def close_month(
    db_path: Path,
    budget_config: dict[str, Any],
    month_date: date,
    *,
    closed_at: str | None = None,
) -> dict[str, Any]:
    settings = settings_from_config(budget_config)
    storage.init_db(db_path)
    month_start = month_date.replace(day=1)
    days_in_month = monthrange(month_date.year, month_date.month)[1]
    month_end = month_date.replace(day=days_in_month)
    with storage.connect(db_path) as conn:
        discretionary_spend = discretionary_spend_for_range(conn, month_start, month_end, settings)
        daily_allowance = float(settings["daily_allowance"])
        result = round((daily_allowance * days_in_month) - discretionary_spend, 2)
        month_key = month_start.strftime("%Y-%m")
        entry = {
            "month": month_key,
            "result": _round_money(result),
            "daily_allowance": _round_money(daily_allowance),
            "discretionary_spend": _round_money(discretionary_spend),
            "days_in_month": days_in_month,
            "closed_at": closed_at or date.today().isoformat(),
        }
        conn.execute(
            """
            INSERT INTO one_number_ledger (
                month_key, result, daily_allowance, discretionary_spend, closed_at, details_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(month_key) DO UPDATE SET
                result = excluded.result,
                daily_allowance = excluded.daily_allowance,
                discretionary_spend = excluded.discretionary_spend,
                closed_at = excluded.closed_at,
                details_json = excluded.details_json
            """,
            (
                month_key,
                result,
                daily_allowance,
                discretionary_spend,
                entry["closed_at"],
                json.dumps(entry, sort_keys=True),
            ),
        )
        conn.commit()
    return entry


def ledger_entries(db_path: Path, limit: int = 12) -> list[dict[str, Any]]:
    storage.init_db(db_path)
    with storage.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT month_key, result, daily_allowance, discretionary_spend, closed_at
            FROM one_number_ledger
            ORDER BY month_key DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "month": row["month_key"],
            "result": _round_money(row["result"]),
            "month_result": _round_money(row["result"]),
            "daily_allowance": _round_money(row["daily_allowance"]),
            "discretionary_spend": _round_money(row["discretionary_spend"]),
            "closed_at": row["closed_at"],
            "state": "negative" if float(row["result"] or 0.0) < 0 else "positive",
        }
        for row in rows
    ]


def settings_export(budget_config: dict[str, Any]) -> dict[str, Any]:
    settings = settings_from_config(budget_config)
    return {
        "daily_allowance": _round_money(settings["daily_allowance"]),
        "excluded_keywords": settings["excluded_keywords"],
        "excluded_categories": settings["excluded_categories"],
        "excluded_payees": settings["excluded_payees"],
        "preset_amounts": settings["preset_amounts"],
        "monthly_reset_day": settings["reset_day"],
        "monthly_reset_time": settings["reset_time"],
        "timezone": "America/Phoenix",
    }


def _clean_strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def _normalized_set(values: Any) -> set[str]:
    return {_normalize(item) for item in values if _normalize(item)}


def _normalize(value: Any) -> str:
    return str(value or "").strip().casefold()


def _round_money(value: Any) -> float:
    return round(float(value or 0.0), 2)


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
