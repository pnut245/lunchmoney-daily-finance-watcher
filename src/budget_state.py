"""Build a compact budget snapshot JSON and lockscreen PNG."""

from __future__ import annotations

import json
from calendar import monthrange
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from . import alarms, lockscreen, one_number, storage


RUNTIME_DIR = Path.home() / "Library" / "Application Support" / "ief-lockscreen"
WIDGET_RUNTIME_DIR = Path.home() / "Library" / "Application Support" / "lunchmoney-finance-watcher"


def refresh_budget_state(
    db_path: Path,
    budget_config: dict[str, Any],
    run_date: date,
    *,
    active_alarms: list[dict[str, Any]] | None = None,
    project_root: Path | None = None,
) -> dict[str, list[Path]]:
    payload = build_budget_state_payload(db_path, budget_config, run_date, active_alarms=active_alarms)
    settings_payload = one_number.settings_export(budget_config)
    ledger_payload = one_number.ledger_entries(db_path, limit=24)
    roots = _output_roots(project_root)

    json_paths: list[Path] = []
    widget_paths: list[Path] = []
    png_paths: list[Path] = []
    settings_paths: list[Path] = []
    ledger_paths: list[Path] = []
    image = lockscreen.render_lockscreen(payload)
    widget_payload = build_widget_snapshot_payload(payload)

    for root in roots:
        json_path = root / "budget_state.json"
        widget_path = root / "widget_snapshot.json"
        settings_path = root / "settings.json"
        ledger_path = root / "ledger.json"
        png_path = root / "lockscreen_latest.png"
        root.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        widget_path.write_text(json.dumps(widget_payload, indent=2) + "\n", encoding="utf-8")
        settings_path.write_text(json.dumps(settings_payload, indent=2) + "\n", encoding="utf-8")
        ledger_path.write_text(json.dumps(ledger_payload, indent=2) + "\n", encoding="utf-8")
        image.save(png_path, format="PNG")
        json_paths.append(json_path)
        widget_paths.append(widget_path)
        settings_paths.append(settings_path)
        ledger_paths.append(ledger_path)
        png_paths.append(png_path)

    return {
        "json_paths": json_paths,
        "widget_paths": widget_paths,
        "settings_paths": settings_paths,
        "ledger_paths": ledger_paths,
        "png_paths": png_paths,
    }


def build_budget_state_payload(
    db_path: Path,
    budget_config: dict[str, Any],
    run_date: date,
    *,
    active_alarms: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    with storage.connect(db_path) as conn:
        cash_balance = _available_cash_balance(conn)
        discretionary_context = _discretionary_context(conn, run_date, budget_config)
        if active_alarms is None:
            run_id = storage.latest_rule_run_id(db_path, run_date)
            active_alarms = (
                alarms.evaluate_alarms(db_path, run_id, run_date, budget_config)
                if run_id is not None
                else []
            )

    lockscreen_config = budget_config.get("lockscreen", {})
    today_amount = round(max(discretionary_context["today_allowance"], 0.0), 2)
    week_amount = round(max(discretionary_context["week_allowance"], 0.0), 2)
    dopamine_amount = round(
        max(
            min(
                today_amount * float(lockscreen_config.get("dopamine_ratio_of_today", 0.85)),
                _as_float(lockscreen_config.get("dopamine_daily_cap")) or today_amount,
                today_amount,
            ),
            0.0,
        ),
        2,
    )
    warning_count = sum(1 for alarm in active_alarms if alarm.get("severity") == "warning")
    critical_count = sum(1 for alarm in active_alarms if alarm.get("severity") == "critical")
    state_name = _spending_state(
        today_amount,
        week_amount,
        critical_count,
        warning_count,
        cash_balance,
        budget_config,
    )
    object_name = _money_object_for_amount(today_amount)

    one_number_state = one_number.build_state(
        db_path,
        budget_config,
        run_date,
        last_updated=datetime.now(UTC).isoformat(),
    )
    ledger = one_number.ledger_entries(db_path, limit=12)
    remaining_today = float(one_number_state["remaining_today"])

    display_state = "NEGATIVE" if one_number_state["is_negative"] else "OK"
    display_amount = _money(remaining_today)

    return {
        **one_number_state,
        "safe_to_spend": display_amount,
        "spending_state": display_state,
        "money_object": object_name,
        "today": display_amount,
        "week": _money(week_amount),
        "dopamine": _money(dopamine_amount),
        "vault_state": _vault_state(cash_balance, budget_config),
        "ledger": ledger,
        "meta": {
            "source": "lunchmoney-daily-finance-watcher",
            "product": "One Number Today",
            "run_date": run_date.isoformat(),
            "critical_alarms": critical_count,
            "warning_alarms": warning_count,
            "daily_allowance": one_number_state["daily_allowance"],
            "today_discretionary_spend": one_number_state["today_discretionary_spend"],
            "remaining_today": one_number_state["remaining_today"],
            "is_negative": one_number_state["is_negative"],
            "safe_to_spend_value": remaining_today,
            "discretionary_monthly_limit": discretionary_context["monthly_limit"],
            "discretionary_month_to_date_spend": discretionary_context["month_to_date_spend"],
            "discretionary_remaining": discretionary_context["remaining"],
            "days_remaining_in_month": discretionary_context["days_remaining"],
            "available_cash_balance": cash_balance,
            "legacy_spending_state": state_name,
            "legacy_safe_to_spend_value": today_amount,
            "money_object": object_name,
        },
    }


def build_widget_snapshot_payload(payload: dict[str, Any]) -> dict[str, Any]:
    remaining_today = float(payload.get("remaining_today", 0.0) or 0.0)

    return {
        "daily_allowance": float(payload.get("daily_allowance", 0.0) or 0.0),
        "today_discretionary_spend": float(payload.get("today_discretionary_spend", 0.0) or 0.0),
        "spent_today": float(payload.get("spent_today", payload.get("today_discretionary_spend", 0.0)) or 0.0),
        "remaining_today": remaining_today,
        "is_negative": bool(payload.get("is_negative", remaining_today < 0)),
        "state": payload.get("state", "positive"),
        "last_updated": payload.get("last_updated"),
        "updated_at": payload.get("updated_at", payload.get("last_updated")),
    }


def _discretionary_context(conn: Any, run_date: date, budget_config: dict[str, Any]) -> dict[str, float | int | None]:
    policy = budget_config.get("budget", {}).get("discretionary_total", {})
    monthly_limit = _as_float(policy.get("monthly_limit")) if policy.get("enabled", False) else None
    categories = [
        str(item.get("name") or "").strip()
        for item in budget_config.get("budget", {}).get("categories", [])
        if item.get("discretionary") and item.get("name")
    ]
    month_start = run_date.replace(day=1)
    month_end = run_date.replace(day=monthrange(run_date.year, run_date.month)[1])
    days_remaining = max((month_end - run_date).days + 1, 1)
    week_days = max(int(budget_config.get("lockscreen", {}).get("weekly_spend_days", 5)), 1)
    month_to_date_spend = sum(
        alarms._category_spend(conn, month_start, run_date, category)
        for category in categories
    )
    if monthly_limit is None:
        monthly_limit = month_to_date_spend
    remaining = max(monthly_limit - month_to_date_spend, 0.0)
    today_allowance = remaining / days_remaining if days_remaining else remaining
    week_allowance = min(remaining, today_allowance * min(week_days, days_remaining))
    return {
        "monthly_limit": round(monthly_limit, 2),
        "month_to_date_spend": round(month_to_date_spend, 2),
        "remaining": round(remaining, 2),
        "days_remaining": days_remaining,
        "today_allowance": today_allowance,
        "week_allowance": week_allowance,
    }


def _available_cash_balance(conn: Any) -> float | None:
    row = conn.execute(
        """
        SELECT COALESCE(SUM(balance), 0) AS balance
        FROM accounts
        WHERE COALESCE(status, 'active') = 'active'
          AND LOWER(COALESCE(type, '')) IN ('depository', 'cash')
        """
    ).fetchone()
    if row is None:
        return None
    return round(float(row["balance"] or 0.0), 2)


def _vault_state(cash_balance: float | None, budget_config: dict[str, Any]) -> str:
    policy = budget_config.get("budget", {}).get("cash_buffer", {})
    minimum = _as_float(policy.get("minimum_balance"))
    if cash_balance is None:
        return "UNKNOWN"
    if not policy.get("enabled", False) or minimum is None:
        return "SAFE"
    return "SAFE" if cash_balance >= minimum else "LOW"


def _spending_state(
    today: float,
    week: float,
    critical_count: int,
    warning_count: int,
    cash_balance: float | None,
    budget_config: dict[str, Any],
) -> str:
    if today < 0:
        return "OVERDRAWN"
    if critical_count or week <= 0 or today <= 0:
        return "DANGER"
    if cash_balance is not None and _vault_state(cash_balance, budget_config) == "LOW" and today < 15:
        return "DANGER"
    if today < 12:
        return "TIGHT"
    if warning_count >= 2 or today < 25:
        return "WATCH IT"
    if warning_count or today < 60:
        return "COMFORTABLE"
    return "PLENTY"


def _money_object_for_amount(today: float) -> str:
    if today <= 0:
        return "No Spend"
    if today < 8:
        return "Coffee"
    if today < 18:
        return "Lunch"
    if today < 35:
        return "Groceries"
    if today < 60:
        return "Dinner"
    if today < 120:
        return "Errands"
    if today < 250:
        return "Day Out"
    return "Big Spend"


def _output_roots(project_root: Path | None) -> list[Path]:
    roots: list[Path] = []
    if project_root is not None:
        roots.append((project_root / "data").resolve())
    if RUNTIME_DIR.exists():
        roots.append(RUNTIME_DIR.resolve())
    if WIDGET_RUNTIME_DIR.exists():
        roots.append(WIDGET_RUNTIME_DIR.resolve())
    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        unique.append(root)
    return unique


def _money(value: float | None) -> str:
    if value is None:
        return "$0"
    rounded = round(value)
    if abs(value - rounded) < 0.005:
        return f"${rounded:,.0f}"
    return f"${value:,.2f}"


def _money_string_to_number(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace("$", "").replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
