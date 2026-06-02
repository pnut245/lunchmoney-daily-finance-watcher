"""Weekly budget email draft and optional SMTP sender."""

from __future__ import annotations

import json
import os
import shutil
import smtplib
from datetime import date, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from . import alarms, storage


def write_weekly_email(
    db_path: Path,
    reports_root: Path,
    run_id: int,
    run_date: date,
    budget_config: dict[str, Any],
    *,
    sample: bool = False,
) -> tuple[Path, str]:
    weekly_root = reports_root / "weekly"
    weekly_root.mkdir(parents=True, exist_ok=True)
    report_path = weekly_root / f"{run_date.isoformat()}.md"
    latest_path = weekly_root / "latest.md"
    markdown = build_weekly_email(db_path, run_id, run_date, budget_config, sample=sample)
    report_path.write_text(markdown, encoding="utf-8")
    shutil.copyfile(report_path, latest_path)
    return report_path, markdown


def build_weekly_email(
    db_path: Path,
    run_id: int,
    run_date: date,
    budget_config: dict[str, Any],
    *,
    sample: bool = False,
) -> str:
    email_config = budget_config.get("weekly_email", {})
    lookback_days = int(email_config.get("lookback_days", 7))
    include_today = bool(email_config.get("include_today", False))
    end_date = run_date if include_today else run_date - timedelta(days=1)
    start_date = end_date - timedelta(days=max(lookback_days - 1, 0))
    month_start = run_date.replace(day=1)
    active_alarms = _dedupe_weekly_alarms(
        alarms.evaluate_alarms(db_path, run_id, run_date, budget_config)
    )
    action_items, watchlist_items = _split_review_items(active_alarms)

    with storage.connect(db_path) as conn:
        weekly_spend = _spend_between(conn, start_date, end_date)
        month_spend = _spend_between(conn, month_start, run_date)
        category_rows = _category_spend(conn, start_date, end_date)
        top_transactions = _top_transactions(conn, start_date, end_date)
        local_budget_rows = _local_budget_progress(conn, run_date, budget_config)

    sample_label = " [SAMPLE MOCK DATA]" if sample else ""
    subject = email_config.get("subject", "Weekly budget review")
    session = email_config.get("budgeting_session", "Sunday afternoon")
    max_agenda_items = int(email_config.get("max_agenda_items", 6))
    max_watchlist_items = int(email_config.get("max_watchlist_items", 6))
    include_info = bool(email_config.get("include_info_in_agenda", False))
    agenda_items = active_alarms if include_info else action_items
    lines = [
        f"# Sunday Budget Brief{sample_label}",
        "",
        f"Subject: {subject}",
        f"Budgeting session: {session}",
        f"Review window: {start_date.isoformat()} to {end_date.isoformat()}",
        f"Generated: {run_date.isoformat()}",
        "",
    ]
    if sample:
        lines.extend(["> Mocked sample data only.", ""])

    lines.extend(
        [
            "## Quick Read",
            "",
            f"- Weekly spend: {_money(weekly_spend)}",
            f"- Month-to-date spend: {_money(month_spend)}",
            f"- Review items: {len(active_alarms)}",
            f"- Needs action: {len(action_items)}",
            f"- Watchlist: {len(watchlist_items)}",
            f"- Budget categories configured: {len(local_budget_rows)}",
            "",
        ]
    )

    takeaways = _weekly_takeaways(action_items, watchlist_items, category_rows)
    if takeaways:
        lines.extend(["## What Matters This Week", ""])
        for takeaway in takeaways:
            lines.append(f"- {takeaway}")
        lines.append("")

    delegation_items = _delegation_items(
        action_items,
        watchlist_items,
        local_budget_rows,
        int(email_config.get("max_delegation_items", 5)),
    )
    if delegation_items:
        lines.extend(["## Delegate First", ""])
        for item in delegation_items:
            lines.append(f"- [ ] {item}")
        lines.append("")

    if bool(email_config.get("include_shareable_context", True)):
        shareable_context = _shareable_context(
            action_items, watchlist_items, category_rows, local_budget_rows
        )
        if shareable_context:
            lines.extend(["## Shareable Context", ""])
            for item in shareable_context:
                lines.append(f"- {item}")
            lines.append("")

    nudges = _cost_value_nudges(
        action_items,
        watchlist_items,
        category_rows,
        local_budget_rows,
        top_transactions,
        int(email_config.get("max_cost_value_nudges", 4)),
    )
    if nudges:
        lines.extend(["## Cost / Value Nudges", ""])
        for nudge in nudges:
            lines.append(f"- {nudge}")
        lines.append("")

    lines.extend(["## Sunday Afternoon Agenda", ""])
    if agenda_items:
        grouped = _group_agenda_items(agenda_items[:max_agenda_items])
        for group_name, items in grouped.items():
            if not items:
                continue
            lines.append(f"### {group_name}")
            for alarm in items:
                lines.append(f"- [ ] {alarm['title']} ({_money(alarm.get('amount'))})")
            lines.append("")
        if len(agenda_items) > max_agenda_items:
            lines.append(f"- [ ] Review {len(agenda_items) - max_agenda_items} more item(s) in the alarm detail report.")
    else:
        lines.append("- [ ] No action items. Do a light budget check and tune thresholds if needed.")
        lines.append("")
    lines.extend(
        [
            "- [ ] Confirm upcoming bills/subscriptions for the next 7 days.",
            "- [ ] Decide whether any flagged spending should change next week's behavior.",
            "- [ ] Update `config/budget.yaml` if a threshold is too noisy or too quiet.",
            "",
        ]
    )

    lines.extend(["## Review Items", ""])
    if action_items:
        lines.extend(["| Severity | Trigger | Amount |", "| --- | --- | ---: |"])
        for alarm in action_items:
            lines.append(f"| {alarm['severity']} | {_escape_table(alarm['title'])} | {_money(alarm.get('amount'))} |")
    else:
        lines.append("No action-level review items.")
    lines.append("")

    lines.extend(["## Watchlist", ""])
    if watchlist_items:
        for alarm in watchlist_items[:max_watchlist_items]:
            lines.append(f"- {alarm['title']} ({_money(alarm.get('amount'))})")
        if len(watchlist_items) > max_watchlist_items:
            lines.append(f"- {len(watchlist_items) - max_watchlist_items} more watchlist item(s).")
    else:
        lines.append("No low-priority watchlist items.")
    lines.append("")

    lines.extend(["## Spend By Category", ""])
    if category_rows:
        lines.extend(["| Category | Weekly Spend |", "| --- | ---: |"])
        for row in category_rows[:15]:
            lines.append(f"| {_escape_table(row['category_name'])} | {_money(row['spend'])} |")
    else:
        lines.append("No categorized spending in this review window.")
    lines.append("")

    lines.extend(["## Local Budget Progress", ""])
    if local_budget_rows:
        lines.extend(["| Category | MTD Spend | Limit | Used |", "| --- | ---: | ---: | ---: |"])
        for row in local_budget_rows:
            lines.append(
                f"| {_escape_table(row['category'])} | {_money(row['spend'])} | {_money(row['limit'])} | {row['ratio']:.0%} |"
            )
    else:
        lines.append("No category limits are set yet in `config/budget.yaml`.")
    lines.append("")

    lines.extend(["## Top Transactions", ""])
    if top_transactions:
        lines.extend(["| Date | Payee | Amount | Category |", "| --- | --- | ---: | --- |"])
        for row in top_transactions:
            lines.append(
                f"| {row['date']} | {_escape_table(row['payee'])} | {_money(row['amount'])} | {_escape_table(row['category_name'] or 'Uncategorized')} |"
            )
    else:
        lines.append("No transactions found in this review window.")
    lines.append("")

    handoff = {
        "run_date": run_date.isoformat(),
        "review_window": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "weekly_spend": weekly_spend,
        "month_to_date_spend": month_spend,
        "active_alarms": active_alarms,
        "top_categories": category_rows[:10],
        "top_transactions": top_transactions,
        "questions": [
            "What should Patrick do during Sunday afternoon budgeting?",
            "Which alarms are worth keeping as weekly email items?",
            "Which should become urgent notifications?",
            "What category limits should be changed?",
        ],
    }
    if bool(email_config.get("include_chatgpt_json", False)):
        lines.extend(
            [
                "## ChatGPT Handoff",
                "",
                "```json",
                json.dumps(handoff, indent=2, sort_keys=True),
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def send_weekly_email(markdown: str, budget_config: dict[str, Any]) -> None:
    email_config = budget_config.get("weekly_email", {})
    subject = str(email_config.get("subject", "Weekly budget review"))
    to_address = _required_env("BUDGET_EMAIL_TO")
    from_address = _required_env("BUDGET_EMAIL_FROM")
    smtp_host = _required_env("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() not in {"0", "false", "no"}

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_address
    message["To"] = to_address
    message.set_content(markdown)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
        if use_tls:
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)


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


def _category_spend(conn: Any, start: date, end: date) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT COALESCE(c.name, 'Uncategorized') AS category_name, SUM(t.amount) AS spend
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND t.amount > 0
          AND COALESCE(c.is_income, 0) = 0
          AND COALESCE(c.exclude_from_totals, 0) = 0
        GROUP BY COALESCE(c.name, 'Uncategorized')
        ORDER BY spend DESC
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    return [{"category_name": row["category_name"], "spend": float(row["spend"] or 0.0)} for row in rows]


def _top_transactions(conn: Any, start: date, end: date) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT t.date, t.payee, t.original_name, t.amount, c.name AS category_name
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND t.amount > 0
          AND COALESCE(c.is_income, 0) = 0
          AND COALESCE(c.exclude_from_totals, 0) = 0
        ORDER BY t.amount DESC
        LIMIT 12
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    return [
        {
            "date": row["date"],
            "payee": row["payee"] or row["original_name"] or "Unknown payee",
            "amount": float(row["amount"] or 0.0),
            "category_name": row["category_name"],
        }
        for row in rows
    ]


def _local_budget_progress(
    conn: Any, run_date: date, budget_config: dict[str, Any]
) -> list[dict[str, Any]]:
    month_start = run_date.replace(day=1)
    rows = []
    for item in budget_config.get("budget", {}).get("categories", []):
        limit = item.get("monthly_limit")
        if limit is None:
            continue
        category = str(item.get("name") or "").strip()
        if not category:
            continue
        spend = _category_month_spend(conn, month_start, run_date, category)
        limit_float = float(limit)
        rows.append(
            {
                "category": category,
                "spend": spend,
                "limit": limit_float,
                "ratio": spend / limit_float if limit_float else 0.0,
            }
        )
    return sorted(rows, key=lambda row: row["ratio"], reverse=True)


def _dedupe_weekly_alarms(active_alarms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped = []
    daily_spend_group = [
        alarm for alarm in active_alarms if alarm.get("type") == "unusual_daily_spend"
    ]
    grouped_ids = {id(alarm) for alarm in daily_spend_group}

    if daily_spend_group:
        windows = sorted(
            {
                int(alarm.get("details", {}).get("trailing_days"))
                for alarm in daily_spend_group
                if alarm.get("details", {}).get("trailing_days")
            }
        )
        first = daily_spend_group[0].copy()
        first["title"] = "One day of spending was unusually high compared with recent averages"
        first["details"] = {
            **first.get("details", {}),
            "combined_trailing_windows": windows,
            "combined_count": len(daily_spend_group),
        }
        deduped.append(first)

    for alarm in active_alarms:
        if id(alarm) in grouped_ids:
            continue
        deduped.append(alarm)
    return deduped


def _split_review_items(
    active_alarms: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    action_items = []
    watchlist_items = []
    for alarm in active_alarms:
        if alarm.get("severity") in {"critical", "warning"}:
            action_items.append(alarm)
        else:
            watchlist_items.append(alarm)
    return action_items, watchlist_items


def _weekly_takeaways(
    action_items: list[dict[str, Any]],
    watchlist_items: list[dict[str, Any]],
    category_rows: list[dict[str, Any]],
) -> list[str]:
    takeaways = []
    if action_items:
        takeaways.append(f"{len(action_items)} item(s) need a Sunday decision or cleanup.")
    if watchlist_items:
        takeaways.append(f"{len(watchlist_items)} low-priority merchant/item(s) can stay on the watchlist.")
    if category_rows:
        top = category_rows[0]
        takeaways.append(
            f"Highest weekly category spend: {top['category_name']} at {_money(top['spend'])}."
        )
    if not takeaways:
        takeaways.append("Nothing urgent surfaced; use the session to tune budgets and look ahead.")
    return takeaways[:4]


def _cost_value_nudges(
    action_items: list[dict[str, Any]],
    watchlist_items: list[dict[str, Any]],
    category_rows: list[dict[str, Any]],
    local_budget_rows: list[dict[str, Any]],
    top_transactions: list[dict[str, Any]],
    limit: int,
) -> list[str]:
    nudges: list[str] = []
    alarm_types = {item.get("type") for item in action_items}

    if "recurring_amount_change" in alarm_types:
        recurring = next(item for item in action_items if item.get("type") == "recurring_amount_change")
        details = recurring.get("details", {})
        previous = details.get("previous_amount")
        latest = details.get("latest_amount")
        if previous is not None and latest is not None:
            delta = float(latest) - float(previous)
            nudges.append(
                f"Subscription changed by {_money(delta)}; decide keep, downgrade, cancel, or mark as expected."
            )
        else:
            nudges.append("Review changed subscriptions once so recurring spend stays intentional.")

    if "duplicate_charge" in alarm_types:
        nudges.append("Check possible duplicates before paying the card balance; pending items may settle out.")

    if "uncategorized" in alarm_types:
        nudges.append("Categorize uncategorized purchases first; uncategorized spending can skew budget totals.")

    if "high_transaction" in alarm_types:
        top = next(item for item in action_items if item.get("type") == "high_transaction")
        payee = str(top.get("title", "largest purchase")).split(": ", 1)[-1]
        nudges.append(
            f"Mark the large purchase ({payee}, {_money(top.get('amount'))}) as planned or unplanned, then decide whether to offset it."
        )

    if category_rows:
        top_category = category_rows[0]
        nudges.append(
            f"Top weekly category was {top_category['category_name']} at {_money(top_category['spend'])}; pick one small limit or tradeoff for next week."
        )

    if watchlist_items:
        nudges.append("Clear expected new merchants into the ignore list so future Sunday briefs stay quieter.")

    if not local_budget_rows:
        nudges.append("Set 2-3 starting category limits in `config/budget.yaml`; perfect numbers can wait.")

    return _unique(nudges)[: max(limit, 0)]


def _delegation_items(
    action_items: list[dict[str, Any]],
    watchlist_items: list[dict[str, Any]],
    local_budget_rows: list[dict[str, Any]],
    limit: int,
) -> list[str]:
    items: list[str] = []
    by_type = {item.get("type"): item for item in action_items}

    if "uncategorized" in by_type:
        alarm = by_type["uncategorized"]
        items.append(f"Categorize or gather receipt context for: {alarm['title']}.")

    if "duplicate_charge" in by_type:
        alarm = by_type["duplicate_charge"]
        items.append(f"Verify whether this is a duplicate charge: {alarm['title']}.")

    if "recurring_amount_change" in by_type:
        alarm = by_type["recurring_amount_change"]
        items.append(f"Confirm whether the subscription increase is expected: {alarm['title']}.")

    if "high_transaction" in by_type:
        alarm = by_type["high_transaction"]
        payee = str(alarm.get("title", "large purchase")).split(": ", 1)[-1]
        items.append(f"Mark {payee} as planned, reimbursable, business, or discretionary.")

    if watchlist_items:
        items.append("Review new merchants and move expected ones to the ignore list.")

    if not local_budget_rows:
        items.append("Set starter limits for the first 2-3 budget categories.")

    return _unique(items)[: max(limit, 0)]


def _shareable_context(
    action_items: list[dict[str, Any]],
    watchlist_items: list[dict[str, Any]],
    category_rows: list[dict[str, Any]],
    local_budget_rows: list[dict[str, Any]],
) -> list[str]:
    context = [
        f"{len(action_items)} item(s) need action before or during Sunday budgeting.",
        f"{len(watchlist_items)} low-priority item(s) are informational/watchlist only.",
    ]
    if category_rows:
        top = category_rows[0]
        context.append(f"Highest weekly category: {top['category_name']} ({_money(top['spend'])}).")
    if not local_budget_rows:
        context.append("Local category limits are not set yet; this is the next useful setup task.")
    return context


def _group_agenda_items(
    action_items: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    groups = {
        "Categorize": [],
        "Verify": [],
        "Decide": [],
        "Tune Later": [],
    }
    for alarm in action_items:
        alarm_type = alarm.get("type")
        if alarm_type == "uncategorized":
            groups["Categorize"].append(alarm)
        elif alarm_type in {"duplicate_charge", "high_transaction"}:
            groups["Verify"].append(alarm)
        elif alarm_type in {
            "recurring_amount_change",
            "category_budget_pacing",
            "category_budget_exceeded",
            "discretionary_budget_exceeded",
            "unusual_daily_spend",
        }:
            groups["Decide"].append(alarm)
        else:
            groups["Tune Later"].append(alarm)
    return groups


def _unique(items: list[str]) -> list[str]:
    seen = set()
    unique_items = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique_items.append(item)
    return unique_items


def _category_month_spend(conn: Any, start: date, end: date, category: str) -> float:
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
        (start.isoformat(), end.isoformat(), category),
    ).fetchone()
    return float(row["spend"] or 0.0)


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _money(value: Any) -> str:
    if value is None:
        return "-"
    return f"${float(value):,.2f}"


def _escape_table(value: Any) -> str:
    return str(value or "").replace("|", "\\|")
