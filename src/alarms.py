"""Trigger-based alarm reports for local budget monitoring."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

from . import rules, storage


def load_budget_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def write_alarm_report(
    db_path: Path,
    reports_root: Path,
    run_id: int,
    run_date: date,
    budget_config: dict[str, Any],
    *,
    sample: bool = False,
) -> tuple[Path, list[dict[str, Any]]]:
    alarms = evaluate_alarms(db_path, run_id, run_date, budget_config)

    alarms_root = reports_root / "alarms"
    alarms_root.mkdir(parents=True, exist_ok=True)
    report_path = alarms_root / f"{run_date.isoformat()}.md"
    latest_path = alarms_root / "latest.md"
    report_path.write_text(
        build_alarm_markdown(db_path, run_id, run_date, budget_config, alarms, sample=sample),
        encoding="utf-8",
    )
    shutil.copyfile(report_path, latest_path)
    return report_path, alarms


def evaluate_alarms(
    db_path: Path, run_id: int, run_date: date, budget_config: dict[str, Any]
) -> list[dict[str, Any]]:
    alarms: list[dict[str, Any]] = []
    with storage.connect(db_path) as conn:
        rule_hits = conn.execute(
            "SELECT * FROM rule_hits WHERE run_id = ? ORDER BY id",
            (run_id,),
        ).fetchall()
        alarms.extend(_promoted_rule_alarms(rule_hits, budget_config))
        alarms.extend(_category_budget_alarms(conn, run_date, budget_config))
        alarms.extend(_discretionary_budget_alarms(conn, run_date, budget_config))
        alarms.extend(_cash_buffer_alarms(conn, budget_config))
        alarms.extend(_monthly_savings_alarms(conn, run_date, budget_config))

    return sorted(alarms, key=_alarm_sort_key)


def build_alarm_markdown(
    db_path: Path,
    run_id: int,
    run_date: date,
    budget_config: dict[str, Any],
    alarms: list[dict[str, Any]],
    *,
    sample: bool = False,
) -> str:
    sample_label = " [SAMPLE MOCK DATA]" if sample else ""
    counts: dict[str, int] = defaultdict(int)
    for alarm in alarms:
        counts[alarm["severity"]] += 1

    lines = [
        f"# Lunch Money Budget Alarms{sample_label}",
        "",
        f"- Date: {run_date.isoformat()}",
        f"- Rule run: {run_id}",
        f"- Active alarms: {len(alarms)}",
        f"- Critical: {counts['critical']}",
        f"- Warning: {counts['warning']}",
        f"- Info: {counts['info']}",
        "",
    ]
    if sample:
        lines.extend(
            [
                "> This is mocked sample data for checking alarm format only.",
                "",
            ]
        )

    if not alarms:
        lines.extend(
            [
                "## Status",
                "",
                "No active budget alarms.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "## Active Alarms",
                "",
                "| Severity | Trigger | Amount | Resource |",
                "| --- | --- | ---: | --- |",
            ]
        )
        for alarm in alarms:
            lines.append(
                "| {severity} | {title} | {amount} | {resource} |".format(
                    severity=alarm["severity"],
                    title=_escape_table(alarm["title"]),
                    amount=_money(alarm.get("amount")),
                    resource=_escape_table(_resource_title(budget_config, alarm.get("resource"))),
                )
            )
        lines.append("")

        lines.extend(["## Resource Engagement", ""])
        for alarm in alarms:
            lines.extend(_resource_block(budget_config, alarm))

    lines.extend(
        [
            "## ChatGPT Handoff",
            "",
            "```text",
            "Review these Lunch Money budget alarms. Separate urgent action from noise, recommend specific threshold changes, and suggest whether each item should become an alert, a weekly review item, or dashboard-only context.",
            "```",
            "",
            "```json",
            json.dumps(_handoff_context(run_date, alarms), indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def send_local_notification(alarms: list[dict[str, Any]], budget_config: dict[str, Any]) -> bool:
    notify_on = set(budget_config.get("alarms", {}).get("notify_on", []))
    notifying = [alarm for alarm in alarms if alarm["type"] in notify_on]
    if not notifying:
        return False

    title = f"{len(notifying)} Lunch Money budget alarm(s)"
    body = "; ".join(alarm["title"] for alarm in notifying[:3])
    if platform.system() == "Darwin":
        script = (
            f'display notification "{_osascript_escape(body)}" '
            f'with title "{_osascript_escape(title)}"'
        )
        subprocess.run(["osascript", "-e", script], check=False)
        return True
    return False


def _promoted_rule_alarms(rule_hits: list[Any], budget_config: dict[str, Any]) -> list[dict[str, Any]]:
    promotions = budget_config.get("alarms", {}).get("promote_rule_hits", {})
    alarms = []
    for row in rule_hits:
        policy = promotions.get(row["rule_name"])
        if not policy:
            continue
        alarms.append(
            {
                "type": row["rule_name"],
                "severity": policy.get("severity", "info"),
                "title": row["title"],
                "amount": row["amount"],
                "date": row["date"],
                "resource": policy.get("resource"),
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "details": rules.details_from_row(row),
            }
        )
    return alarms


def _category_budget_alarms(
    conn: Any, run_date: date, budget_config: dict[str, Any]
) -> list[dict[str, Any]]:
    budgets = budget_config.get("budget", {}).get("categories", [])
    month_start = run_date.replace(day=1)
    month_end = _month_end(run_date)
    alarms = []
    for item in budgets:
        limit = _as_float(item.get("monthly_limit"))
        if limit is None or limit <= 0:
            continue
        category_name = str(item.get("name") or "").strip()
        if not category_name:
            continue
        spending = _category_spend(conn, month_start, run_date, category_name)
        if spending <= 0:
            continue
        ratio = spending / limit
        warning_at = float(item.get("warning_at_ratio", 0.85))
        alarm_at = float(item.get("alarm_at_ratio", 1.0))
        expected_ratio = _elapsed_ratio(month_start, month_end, run_date)
        if ratio >= alarm_at:
            alarms.append(
                _budget_alarm(
                    "category_budget_exceeded",
                    "critical",
                    f"{category_name} budget exceeded",
                    spending,
                    category_name,
                    limit,
                    ratio,
                    expected_ratio,
                )
            )
        elif ratio >= warning_at and ratio > expected_ratio * 1.15:
            alarms.append(
                _budget_alarm(
                    "category_budget_pacing",
                    "warning",
                    f"{category_name} budget pacing high",
                    spending,
                    category_name,
                    limit,
                    ratio,
                    expected_ratio,
                )
            )
    return alarms


def _discretionary_budget_alarms(
    conn: Any, run_date: date, budget_config: dict[str, Any]
) -> list[dict[str, Any]]:
    policy = budget_config.get("budget", {}).get("discretionary_total", {})
    if not policy.get("enabled", False):
        return []
    limit = _as_float(policy.get("monthly_limit"))
    if limit is None or limit <= 0:
        return []
    categories = [
        str(item.get("name"))
        for item in budget_config.get("budget", {}).get("categories", [])
        if item.get("discretionary") and item.get("name")
    ]
    if not categories:
        return []

    month_start = run_date.replace(day=1)
    month_end = _month_end(run_date)
    spending = sum(_category_spend(conn, month_start, run_date, name) for name in categories)
    ratio = spending / limit
    warning_at = float(policy.get("warning_at_ratio", 0.85))
    alarm_at = float(policy.get("alarm_at_ratio", 1.0))
    expected_ratio = _elapsed_ratio(month_start, month_end, run_date)
    if ratio >= alarm_at:
        severity = "critical"
        alarm_type = "discretionary_budget_exceeded"
        title = "Discretionary budget exceeded"
    elif ratio >= warning_at and ratio > expected_ratio * 1.15:
        severity = "warning"
        alarm_type = "discretionary_budget_pacing"
        title = "Discretionary budget pacing high"
    else:
        return []
    return [
        {
            "type": alarm_type,
            "severity": severity,
            "title": title,
            "amount": round(spending, 2),
            "date": run_date.isoformat(),
            "resource": "spending_slowdown",
            "entity_type": "budget",
            "entity_id": "discretionary_total",
            "details": {
                "monthly_limit": limit,
                "spending": round(spending, 2),
                "ratio": round(ratio, 3),
                "expected_ratio": round(expected_ratio, 3),
                "categories": categories,
            },
        }
    ]


def _cash_buffer_alarms(conn: Any, budget_config: dict[str, Any]) -> list[dict[str, Any]]:
    policy = budget_config.get("budget", {}).get("cash_buffer", {})
    if not policy.get("enabled", False):
        return []
    minimum = _as_float(policy.get("minimum_balance"))
    if minimum is None:
        return []
    names = {str(name).strip().lower() for name in policy.get("account_names", []) if str(name).strip()}
    rows = conn.execute(
        """
        SELECT name, display_name, type, balance, status
        FROM accounts
        WHERE COALESCE(status, 'active') = 'active'
        """
    ).fetchall()
    included = []
    balance = 0.0
    for row in rows:
        label = (row["display_name"] or row["name"] or "").strip()
        account_type = str(row["type"] or "").lower()
        if names and label.lower() not in names:
            continue
        if not names and account_type not in {"cash", "depository", "checking", "savings"}:
            continue
        included.append(label)
        balance += float(row["balance"] or 0.0)
    if balance >= minimum:
        return []
    return [
        {
            "type": "cash_buffer_low",
            "severity": "critical",
            "title": "Cash buffer below target",
            "amount": round(balance, 2),
            "date": None,
            "resource": "cash_buffer_review",
            "entity_type": "account_group",
            "entity_id": "cash_buffer",
            "details": {
                "minimum_balance": minimum,
                "current_balance": round(balance, 2),
                "included_accounts": included,
            },
        }
    ]


def _monthly_savings_alarms(
    conn: Any, run_date: date, budget_config: dict[str, Any]
) -> list[dict[str, Any]]:
    policy = budget_config.get("budget", {}).get("monthly_savings_target", {})
    if not policy.get("enabled", False):
        return []
    target = _as_float(policy.get("amount"))
    if target is None:
        return []
    month_start = run_date.replace(day=1)
    row = conn.execute(
        """
        SELECT
          COALESCE(SUM(CASE WHEN t.amount < 0 THEN ABS(t.amount) ELSE 0 END), 0) AS inflow,
          COALESCE(SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END), 0) AS outflow
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND COALESCE(c.exclude_from_totals, 0) = 0
        """,
        (month_start.isoformat(), run_date.isoformat()),
    ).fetchone()
    current_savings = float(row["inflow"] or 0.0) - float(row["outflow"] or 0.0)
    expected_target = target * _elapsed_ratio(month_start, _month_end(run_date), run_date)
    if current_savings >= expected_target:
        return []
    return [
        {
            "type": "monthly_savings_pacing",
            "severity": "warning",
            "title": "Monthly savings target pacing low",
            "amount": round(current_savings, 2),
            "date": run_date.isoformat(),
            "resource": "spending_slowdown",
            "entity_type": "budget",
            "entity_id": "monthly_savings_target",
            "details": {
                "target": target,
                "expected_target_to_date": round(expected_target, 2),
                "current_savings": round(current_savings, 2),
            },
        }
    ]


def _category_spend(conn: Any, start: date, end: date, category_name: str) -> float:
    row = conn.execute(
        """
        SELECT COALESCE(SUM(t.amount), 0) AS spend
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND LOWER(c.name) = LOWER(?)
          AND t.amount > 0
          AND COALESCE(c.is_income, 0) = 0
          AND COALESCE(c.exclude_from_totals, 0) = 0
        """,
        (start.isoformat(), end.isoformat(), category_name),
    ).fetchone()
    return float(row["spend"] or 0.0)


def _budget_alarm(
    alarm_type: str,
    severity: str,
    title: str,
    spending: float,
    category_name: str,
    limit: float,
    ratio: float,
    expected_ratio: float,
) -> dict[str, Any]:
    return {
        "type": alarm_type,
        "severity": severity,
        "title": title,
        "amount": round(spending, 2),
        "date": None,
        "resource": "budget_pacing_review",
        "entity_type": "category",
        "entity_id": category_name,
        "details": {
            "category_name": category_name,
            "monthly_limit": limit,
            "spending": round(spending, 2),
            "ratio": round(ratio, 3),
            "expected_ratio": round(expected_ratio, 3),
        },
    }


def _resource_block(budget_config: dict[str, Any], alarm: dict[str, Any]) -> list[str]:
    resource_id = alarm.get("resource")
    resource = budget_config.get("resources", {}).get(resource_id, {})
    title = resource.get("title") or resource_id or "Review"
    lines = [
        f"### {alarm['severity'].upper()}: {alarm['title']}",
        "",
        f"- Resource: {title}",
    ]
    if alarm.get("amount") is not None:
        lines.append(f"- Amount: {_money(alarm['amount'])}")
    details = alarm.get("details") or {}
    if details:
        lines.append(f"- Context: `{json.dumps(details, sort_keys=True)}`")
    actions = resource.get("actions") or []
    if actions:
        lines.append("- Actions:")
        for action in actions:
            lines.append(f"  - {action}")
    lines.append("")
    return lines


def _handoff_context(run_date: date, alarms: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "date": run_date.isoformat(),
        "active_alarm_count": len(alarms),
        "alarms": alarms,
        "review_questions": [
            "Which alarms should interrupt Patrick immediately?",
            "Which should be weekly-review only?",
            "Which thresholds are too noisy?",
            "What resource or next action should be attached to each trigger?",
        ],
    }


def _resource_title(budget_config: dict[str, Any], resource_id: str | None) -> str:
    if not resource_id:
        return ""
    resource = budget_config.get("resources", {}).get(resource_id, {})
    return resource.get("title") or resource_id


def _alarm_sort_key(alarm: dict[str, Any]) -> tuple[int, str]:
    severity_rank = {"critical": 0, "warning": 1, "info": 2}
    return (severity_rank.get(alarm.get("severity"), 9), alarm.get("title", ""))


def _elapsed_ratio(start: date, end: date, current: date) -> float:
    total_days = max((end - start).days + 1, 1)
    elapsed_days = max((current - start).days + 1, 1)
    return min(elapsed_days / total_days, 1.0)


def _month_end(day: date) -> date:
    if day.month == 12:
        return date(day.year, 12, 31)
    return date(day.year, day.month + 1, 1) - timedelta(days=1)


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _money(value: Any) -> str:
    if value is None:
        return "-"
    return f"${float(value):,.2f}"


def _escape_table(value: Any) -> str:
    return str(value or "").replace("|", "\\|")


def _osascript_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
