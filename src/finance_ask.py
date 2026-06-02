"""On-demand finance question context packets.

This module does not call an LLM. It builds a local, reviewable markdown packet
that ChatGPT/Codex can answer from without needing raw API access.
"""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from . import merchant_map, storage


def write_question_packet(
    db_path: Path,
    reports_root: Path,
    question: str,
    ask_date: date,
    rules_config: dict[str, Any],
    budget_config: dict[str, Any],
    merchant_map_path: Path | None = None,
) -> Path:
    storage.init_db(db_path)
    reports_root.mkdir(parents=True, exist_ok=True)
    question_root = reports_root / "questions"
    question_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = question_root / f"{timestamp}.md"
    latest_path = question_root / "latest.md"

    mapping_rules = merchant_map.load_merchant_map(merchant_map_path) if merchant_map_path else []
    context = build_context(db_path, question, ask_date, rules_config, budget_config, mapping_rules)
    markdown = build_markdown(question, context)
    path.write_text(markdown, encoding="utf-8")
    shutil.copyfile(path, latest_path)
    return path


def write_merchant_summary(
    db_path: Path,
    reports_root: Path,
    merchant_query: str,
    ask_date: date,
    days: int = 30,
    merchant_map_path: Path | None = None,
) -> Path:
    storage.init_db(db_path)
    reports_root.mkdir(parents=True, exist_ok=True)
    merchant_root = reports_root / "merchants"
    merchant_root.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r"[^a-z0-9]+", "-", merchant_query.lower()).strip("-") or "merchant"
    path = merchant_root / f"{ask_date.isoformat()}-{safe_name}-{days}d.md"
    latest_path = merchant_root / "latest.md"

    start = ask_date - timedelta(days=max(days - 1, 0))
    mapping_rules = merchant_map.load_merchant_map(merchant_map_path) if merchant_map_path else []
    with storage.connect(db_path) as conn:
        rows = _merchant_transactions(conn, merchant_query, start, ask_date, mapping_rules)

    total = round(sum(float(row["amount"] or 0.0) for row in rows), 2)
    markdown = _merchant_markdown(merchant_query, ask_date, start, days, rows, total)
    path.write_text(markdown, encoding="utf-8")
    shutil.copyfile(path, latest_path)
    return path


def write_purchase_impact(
    db_path: Path,
    reports_root: Path,
    amount: float,
    category: str | None,
    merchant: str | None,
    ask_date: date,
    budget_config: dict[str, Any],
    merchant_map_path: Path | None = None,
) -> Path:
    storage.init_db(db_path)
    reports_root.mkdir(parents=True, exist_ok=True)
    impact_root = reports_root / "impact"
    impact_root.mkdir(parents=True, exist_ok=True)
    latest_path = impact_root / "latest.md"
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = impact_root / f"{timestamp}.md"

    mapping_rules = merchant_map.load_merchant_map(merchant_map_path) if merchant_map_path else []
    context = build_purchase_impact_context(
        db_path,
        amount,
        category,
        merchant,
        ask_date,
        budget_config,
        mapping_rules,
    )
    path.write_text(_purchase_impact_markdown(context), encoding="utf-8")
    shutil.copyfile(path, latest_path)
    return path


def build_purchase_impact_context(
    db_path: Path,
    amount: float,
    category: str | None,
    merchant: str | None,
    ask_date: date,
    budget_config: dict[str, Any],
    mapping_rules: list[dict[str, Any]],
) -> dict[str, Any]:
    suggestion = merchant_map.suggest_for_payee(merchant, mapping_rules) if merchant else None
    resolved_category = category or (suggestion or {}).get("category")
    if not resolved_category:
        resolved_category = "Uncategorized"

    month_start = ask_date.replace(day=1)
    with storage.connect(db_path) as conn:
        category_current = _suggested_category_spend_for_name(conn, month_start, ask_date, resolved_category, mapping_rules)
        discretionary_current = _suggested_discretionary_spend(conn, month_start, ask_date, budget_config, mapping_rules)
        account_balance = _available_cash_balance(conn)

    category_policy = _category_policy(budget_config, resolved_category)
    category_limit = _as_float(category_policy.get("monthly_limit")) if category_policy else None
    category_after = round(category_current + amount, 2)
    category_remaining_before = _remaining(category_limit, category_current)
    category_remaining_after = _remaining(category_limit, category_after)
    category_over_by = _over_by(category_limit, category_after)

    discretionary_policy = budget_config.get("budget", {}).get("discretionary_total", {})
    discretionary_limit = _as_float(discretionary_policy.get("monthly_limit"))
    is_discretionary = bool(category_policy.get("discretionary")) if category_policy else False
    discretionary_after = round(discretionary_current + amount, 2) if is_discretionary else discretionary_current
    discretionary_over_by = _over_by(discretionary_limit, discretionary_after)
    purchase_discretionary_over_by = discretionary_over_by if is_discretionary else 0.0

    decision = _impact_decision(
        amount=amount,
        category=resolved_category,
        category_limit=category_limit,
        category_over_by=category_over_by,
        discretionary_over_by=purchase_discretionary_over_by,
        account_balance=account_balance,
    )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "ask_date": ask_date.isoformat(),
        "amount": amount,
        "merchant": merchant,
        "requested_category": category,
        "resolved_category": resolved_category,
        "merchant_suggestion": suggestion,
        "category": {
            "current_month_spend": round(category_current, 2),
            "after_purchase": category_after,
            "monthly_limit": category_limit,
            "remaining_before": category_remaining_before,
            "remaining_after": category_remaining_after,
            "over_by_after": category_over_by,
            "discretionary": is_discretionary,
        },
        "discretionary_total": {
            "enabled": bool(discretionary_policy.get("enabled", False)),
            "current_month_spend": round(discretionary_current, 2),
            "after_purchase": round(discretionary_after, 2),
            "monthly_limit": discretionary_limit,
            "over_by_after": discretionary_over_by,
        },
        "cash": {
            "available_cash_balance": account_balance,
            "balance_after_purchase": round(account_balance - amount, 2) if account_balance is not None else None,
        },
        "decision": decision,
        "limits": [
            "This is a local estimate, not professional financial advice.",
            "Suggested category spend is based on local merchant-map rules, not confirmed Lunch Money categories.",
            "Pending transactions and account balances may lag behind real life.",
        ],
    }


def build_context(
    db_path: Path,
    question: str,
    ask_date: date,
    rules_config: dict[str, Any],
    budget_config: dict[str, Any],
    mapping_rules: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    mapping_rules = mapping_rules or []
    with storage.connect(db_path) as conn:
        latest_snapshot = conn.execute("SELECT MAX(snapshot_date) AS value FROM snapshots").fetchone()["value"]
        latest_run = conn.execute(
            "SELECT id, run_date, created_at FROM rule_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        latest_hits = []
        if latest_run:
            latest_hits = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT rule_name, severity, title, entity_type, entity_id, date, amount, payee, details_json
                    FROM rule_hits
                    WHERE run_id = ?
                    ORDER BY severity DESC, rule_name, id
                    """,
                    (latest_run["id"],),
                )
            ]

        summary = {
            "today_spend": _spend_between(conn, ask_date, ask_date),
            "last_7_days_spend": _spend_between(conn, ask_date - timedelta(days=6), ask_date),
            "last_30_days_spend": _spend_between(conn, ask_date - timedelta(days=29), ask_date),
            "last_90_days_spend": _spend_between(conn, ask_date - timedelta(days=89), ask_date),
            "month_to_date_spend": _spend_between(conn, ask_date.replace(day=1), ask_date),
            "recent_uncategorized_count": _uncategorized_count(conn, ask_date - timedelta(days=6), ask_date),
            "account_count": _count(conn, "accounts"),
            "recurring_item_count": _count(conn, "recurring_items"),
        }
        summary["average_daily_spend_30d"] = round(summary["last_30_days_spend"] / 30, 2)
        summary["average_daily_spend_90d"] = round(summary["last_90_days_spend"] / 90, 2)

        recent_transactions = _recent_transactions(
            conn, ask_date - timedelta(days=13), ask_date, limit=25, mapping_rules=mapping_rules
        )
        top_payees_30d = _top_payees(
            conn, ask_date - timedelta(days=29), ask_date, mapping_rules=mapping_rules
        )
        category_spend_30d = _category_spend(conn, ask_date - timedelta(days=29), ask_date)
        suggested_category_spend_30d = _suggested_category_spend(
            conn, ask_date - timedelta(days=29), ask_date, mapping_rules
        )
        accounts = _account_summary(conn)

    hit_counts = Counter(hit["rule_name"] for hit in latest_hits)
    question_amount = _extract_amount(question)
    active_alarm_count = len(latest_hits)
    intent = _classify_question(question)
    draft_response = _draft_response(
        question,
        intent,
        question_amount,
        summary,
        latest_hits,
        budget_config,
        suggested_category_spend_30d,
    )

    return {
        "question": question,
        "ask_date": ask_date.isoformat(),
        "generated_at": datetime.now(UTC).isoformat(),
        "intent": intent,
        "question_amount": question_amount,
        "latest_snapshot_date": latest_snapshot,
        "latest_rule_run": dict(latest_run) if latest_run else None,
        "summary": summary,
        "active_alarm_count": active_alarm_count,
        "flags_by_rule": dict(sorted(hit_counts.items())),
        "latest_rule_hits": [_clean_hit(hit) for hit in latest_hits],
        "accounts": accounts,
        "top_payees_30d": top_payees_30d,
        "category_spend_30d": category_spend_30d,
        "suggested_category_spend_30d": suggested_category_spend_30d,
        "recent_transactions": recent_transactions,
        "criteria": _criteria_summary(rules_config, budget_config),
        "draft_response": draft_response,
        "limits": [
            "This is not professional financial advice.",
            "Cash buffer, discretionary category list, merchants to ignore, and savings target are still TODOs unless configured.",
            "Lunch Money categories/recurring/budget data may be incomplete if the API returned empty datasets.",
        ],
    }


def build_markdown(question: str, context: dict[str, Any]) -> str:
    summary = context["summary"]
    criteria = context["criteria"]
    lines = [
        "# Finance Question Packet",
        "",
        f"- Generated at: {context['generated_at']}",
        f"- Ask date: {context['ask_date']}",
        f"- Latest Lunch Money snapshot: {context['latest_snapshot_date'] or 'none'}",
        f"- Question: {question}",
        f"- Intent guess: {context['intent']}",
        f"- Active rule hits: {context['active_alarm_count']}",
        "",
        "## Draft Response",
        "",
        context["draft_response"],
        "",
        "## Quick Context",
        "",
        f"- Spend today: {_money(summary['today_spend'])}",
        f"- Spend last 7 days: {_money(summary['last_7_days_spend'])}",
        f"- Spend last 30 days: {_money(summary['last_30_days_spend'])}",
        f"- Spend month to date: {_money(summary['month_to_date_spend'])}",
        f"- Average daily spend, 30 days: {_money(summary['average_daily_spend_30d'])}",
        f"- Average daily spend, 90 days: {_money(summary['average_daily_spend_90d'])}",
        f"- Recent uncategorized transactions: {summary['recent_uncategorized_count']}",
        "",
        "## Current Criteria",
        "",
        f"- High transaction threshold: {_money(criteria['high_transaction_threshold'])}",
        f"- Duplicate charge window: {criteria['duplicate_charge_window_days']} days",
        f"- Unusual daily spend multiplier: {criteria['unusual_daily_spend_multiplier']}",
        f"- Cash buffer configured: {criteria['cash_buffer_enabled']}",
        f"- Monthly savings target configured: {criteria['monthly_savings_target_enabled']}",
        f"- Discretionary total configured: {criteria['discretionary_total_enabled']}",
        "",
        "## Active Rule Hits",
        "",
    ]

    if context["latest_rule_hits"]:
        lines.extend(["| Rule | Date | Payee | Amount | Title |", "| --- | --- | --- | ---: | --- |"])
        for hit in context["latest_rule_hits"]:
            lines.append(
                "| {rule} | {date} | {payee} | {amount} | {title} |".format(
                    rule=_escape_table(hit["rule_name"]),
                    date=hit["date"] or "",
                    payee=_escape_table(hit["payee"] or ""),
                    amount=_money(hit["amount"]) if hit["amount"] is not None else "",
                    title=_escape_table(hit["title"]),
                )
            )
    else:
        lines.append("No active rule hits in the latest local run.")

    lines.extend(["", "## Top Payees Last 30 Days", ""])
    if context["top_payees_30d"]:
        lines.extend(
            [
                "| Payee | Spend | Count | Suggested Category | Policy |",
                "| --- | ---: | ---: | --- | --- |",
            ]
        )
        for row in context["top_payees_30d"]:
            suggestion = row.get("suggestion") or {}
            lines.append(
                "| {payee} | {spend} | {count} | {category} | {policy} |".format(
                    payee=_escape_table(row["payee"]),
                    spend=_money(row["spend"]),
                    count=row["count"],
                    category=_escape_table(suggestion.get("category", "")),
                    policy=_escape_table(suggestion.get("alert_policy", "")),
                )
            )
    else:
        lines.append("No payee spend available.")

    lines.extend(["", "## Category Spend Last 30 Days", ""])
    if context["category_spend_30d"]:
        lines.extend(["| Category | Spend | Count |", "| --- | ---: | ---: |"])
        for row in context["category_spend_30d"]:
            lines.append(f"| {_escape_table(row['category'])} | {_money(row['spend'])} | {row['count']} |")
    else:
        lines.append("No category spend available.")

    lines.extend(["", "## Suggested Category Spend Last 30 Days", ""])
    if context["suggested_category_spend_30d"]:
        lines.extend(["| Suggested Category | Spend | Count |", "| --- | ---: | ---: |"])
        for row in context["suggested_category_spend_30d"]:
            lines.append(f"| {_escape_table(row['category'])} | {_money(row['spend'])} | {row['count']} |")
    else:
        lines.append("No local merchant-map suggestions matched recent spend.")

    lines.extend(["", "## Accounts Snapshot", ""])
    if context["accounts"]:
        lines.extend(["| Source | Name | Type | Balance | Status |", "| --- | --- | --- | ---: | --- |"])
        for row in context["accounts"]:
            lines.append(
                "| {source} | {name} | {type} | {balance} | {status} |".format(
                    source=_escape_table(row["account_source"]),
                    name=_escape_table(row["name"]),
                    type=_escape_table(row["type"]),
                    balance=_money(row["balance"]) if row["balance"] is not None else "",
                    status=_escape_table(row["status"] or ""),
                )
            )
    else:
        lines.append("No account records available.")

    lines.extend(
        [
            "",
            "## ChatGPT / Codex Review Prompt",
            "",
            "```text",
            "Answer Patrick's finance question using only the structured local context below. Be practical, cautious, and explicit about uncertainty. Separate urgent action from cleanup noise. Do not pretend this is professional financial advice.",
            "```",
            "",
            "## Structured Context",
            "",
            "```json",
            json.dumps(context, indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _merchant_transactions(
    conn: Any,
    merchant_query: str,
    start: date,
    end: date,
    mapping_rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pattern = f"%{merchant_query.lower()}%"
    rows = conn.execute(
        """
        SELECT t.date,
               COALESCE(t.payee, t.original_name, 'Unknown payee') AS payee,
               t.amount,
               COALESCE(c.name, 'Uncategorized') AS category,
               t.status,
               t.is_pending
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND t.amount > 0
          AND lower(COALESCE(t.payee, t.original_name, '')) LIKE ?
        ORDER BY t.date DESC, t.id DESC
        """,
        (start.isoformat(), end.isoformat(), pattern),
    ).fetchall()
    return [
        {
            "date": row["date"],
            "payee": row["payee"],
            "amount": float(row["amount"] or 0.0),
            "category": row["category"],
            "status": row["status"],
            "pending": bool(row["is_pending"]),
            "suggestion": merchant_map.suggest_for_payee(row["payee"], mapping_rules),
        }
        for row in rows
    ]


def _merchant_markdown(
    merchant_query: str,
    ask_date: date,
    start: date,
    days: int,
    rows: list[dict[str, Any]],
    total: float,
) -> str:
    categories = Counter(row["category"] for row in rows)
    pending_count = sum(1 for row in rows if row["pending"])
    lines = [
        "# Merchant Spend Summary",
        "",
        f"- Merchant search: {merchant_query}",
        f"- Window: {start.isoformat()} through {ask_date.isoformat()} ({days} days)",
        f"- Matching purchases: {len(rows)}",
        f"- Total spend: {_money(total)}",
        f"- Pending transactions: {pending_count}",
        "",
    ]
    if categories:
        lines.extend(["## Categories", ""])
        for category, count in sorted(categories.items()):
            category_total = sum(row["amount"] for row in rows if row["category"] == category)
            lines.append(f"- {category}: {_money(category_total)} across {count} purchase(s)")
        lines.append("")

    lines.extend(["## Purchases", ""])
    if rows:
        lines.extend(
            [
                "| Date | Payee | Amount | Category | Suggested Category | Policy | Status |",
                "| --- | --- | ---: | --- | --- | --- | --- |",
            ]
        )
        for row in rows:
            status = row["status"] or ""
            if row["pending"]:
                status = f"{status} pending".strip()
            suggestion = row.get("suggestion") or {}
            lines.append(
                "| {date} | {payee} | {amount} | {category} | {suggested} | {policy} | {status} |".format(
                    date=row["date"],
                    payee=_escape_table(row["payee"]),
                    amount=_money(row["amount"]),
                    category=_escape_table(row["category"]),
                    suggested=_escape_table(suggestion.get("category", "")),
                    policy=_escape_table(suggestion.get("alert_policy", "")),
                    status=_escape_table(status),
                )
            )
    else:
        lines.append("No matching purchases found in the local Lunch Money cache.")
        lines.append("")
        lines.append("Try a broader merchant search term, for example `trader`, `joe`, or the exact payee text from Lunch Money.")
    lines.append("")
    return "\n".join(lines)


def _purchase_impact_markdown(context: dict[str, Any]) -> str:
    category = context["category"]
    discretionary = context["discretionary_total"]
    cash = context["cash"]
    decision = context["decision"]
    lines = [
        "# Purchase Impact",
        "",
        f"- Generated at: {context['generated_at']}",
        f"- Date: {context['ask_date']}",
        f"- Amount: {_money(context['amount'])}",
        f"- Merchant: {context['merchant'] or 'not provided'}",
        f"- Category: {context['resolved_category']}",
        f"- Decision: {decision['status']}",
        "",
        "## Answer",
        "",
        decision["message"],
        "",
        "## Category Impact",
        "",
        f"- Current month spend: {_money(category['current_month_spend'])}",
        f"- After this purchase: {_money(category['after_purchase'])}",
        f"- Monthly limit: {_money(category['monthly_limit']) if category['monthly_limit'] is not None else 'not configured'}",
        f"- Remaining before: {_money(category['remaining_before']) if category['remaining_before'] is not None else 'unknown'}",
        f"- Remaining after: {_money(category['remaining_after']) if category['remaining_after'] is not None else 'unknown'}",
        f"- Over budget after: {_money(category['over_by_after'])}",
        "",
        "## Discretionary Impact",
        "",
        f"- Discretionary budget enabled: {discretionary['enabled']}",
        f"- Current discretionary spend: {_money(discretionary['current_month_spend'])}",
        f"- After this purchase: {_money(discretionary['after_purchase'])}",
        f"- Monthly discretionary limit: {_money(discretionary['monthly_limit']) if discretionary['monthly_limit'] is not None else 'not configured'}",
        f"- Over discretionary budget after: {_money(discretionary['over_by_after'])}",
        "",
        "## Cash Context",
        "",
        f"- Available cash balance: {_money(cash['available_cash_balance']) if cash['available_cash_balance'] is not None else 'unknown'}",
        f"- Balance after purchase: {_money(cash['balance_after_purchase']) if cash['balance_after_purchase'] is not None else 'unknown'}",
        "",
        "## Structured Context",
        "",
        "```json",
        json.dumps(context, indent=2, sort_keys=True),
        "```",
        "",
    ]
    return "\n".join(lines)


def _suggested_category_spend_for_name(
    conn: Any, start: date, end: date, category: str, mapping_rules: list[dict[str, Any]]
) -> float:
    if category == "Uncategorized":
        return _category_spend_amount(conn, start, end, category)
    total = 0.0
    rows = conn.execute(
        """
        SELECT COALESCE(payee, original_name, 'Unknown payee') AS payee,
               amount
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND amount > 0
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    for row in rows:
        suggestion = merchant_map.suggest_for_payee(row["payee"], mapping_rules)
        if suggestion and suggestion.get("category") == category:
            total += float(row["amount"] or 0.0)
    return round(total, 2)


def _suggested_discretionary_spend(
    conn: Any, start: date, end: date, budget_config: dict[str, Any], mapping_rules: list[dict[str, Any]]
) -> float:
    discretionary_categories = {
        str(item.get("name"))
        for item in budget_config.get("budget", {}).get("categories", [])
        if item.get("discretionary") and item.get("name")
    }
    if not discretionary_categories:
        return 0.0
    total = 0.0
    rows = conn.execute(
        """
        SELECT COALESCE(payee, original_name, 'Unknown payee') AS payee,
               amount
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND amount > 0
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    for row in rows:
        suggestion = merchant_map.suggest_for_payee(row["payee"], mapping_rules)
        if suggestion and suggestion.get("category") in discretionary_categories:
            total += float(row["amount"] or 0.0)
    return round(total, 2)


def _category_spend_amount(conn: Any, start: date, end: date, category: str) -> float:
    row = conn.execute(
        """
        SELECT COALESCE(SUM(t.amount), 0) AS spend
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND t.amount > 0
          AND COALESCE(c.name, 'Uncategorized') = ?
        """,
        (start.isoformat(), end.isoformat(), category),
    ).fetchone()
    return round(float(row["spend"] or 0.0), 2)


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


def _category_policy(budget_config: dict[str, Any], category: str) -> dict[str, Any]:
    for item in budget_config.get("budget", {}).get("categories", []):
        if str(item.get("name") or "").lower() == category.lower():
            return item
    return {}


def _remaining(limit: float | None, spend: float) -> float | None:
    if limit is None:
        return None
    return round(limit - spend, 2)


def _over_by(limit: float | None, spend: float) -> float:
    if limit is None:
        return 0.0
    return round(max(spend - limit, 0.0), 2)


def _impact_decision(
    *,
    amount: float,
    category: str,
    category_limit: float | None,
    category_over_by: float,
    discretionary_over_by: float,
    account_balance: float | None,
) -> dict[str, str]:
    if account_balance is not None and amount > account_balance:
        return {
            "status": "NO",
            "message": (
                f"This would exceed the visible cash balance by {_money(amount - account_balance)}. "
                "Do not treat it as affordable without another funding source."
            ),
        }
    if category_limit is None:
        return {
            "status": "UNKNOWN",
            "message": (
                f"I can estimate cash impact, but `{category}` does not have a monthly limit configured yet. "
                f"This purchase would reduce visible cash by {_money(amount)}."
            ),
        }
    if category_over_by > 0:
        return {
            "status": "OVER_BUDGET",
            "message": (
                f"This would put `{category}` over its monthly limit by {_money(category_over_by)}. "
                "Treat it as a review/avoid unless Patrick decides this category limit should move."
            ),
        }
    if discretionary_over_by > 0:
        return {
            "status": "DISCRETIONARY_OVER_BUDGET",
            "message": (
                f"The category itself stays under limit, but discretionary total would be over by {_money(discretionary_over_by)}. "
                "This is a yellow-light purchase."
            ),
        }
    return {
        "status": "OK_WITH_CAUTION",
        "message": (
            f"This appears to stay within the configured `{category}` limit. "
            "Still check current cash and any pending transactions before buying."
        ),
    }


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _draft_response(
    question: str,
    intent: str,
    amount: float | None,
    summary: dict[str, Any],
    hits: list[dict[str, Any]],
    budget_config: dict[str, Any],
    suggested_category_spend: list[dict[str, Any]],
) -> str:
    flags_by_rule = Counter(hit["rule_name"] for hit in hits)
    duplicate_count = flags_by_rule.get("duplicate_charge", 0)
    high_count = flags_by_rule.get("high_transaction", 0)
    uncategorized_count = flags_by_rule.get("uncategorized", 0)
    cash_buffer_enabled = bool(
        budget_config.get("budget", {}).get("cash_buffer", {}).get("enabled", False)
    )
    savings_enabled = bool(
        budget_config.get("budget", {}).get("monthly_savings_target", {}).get("enabled", False)
    )

    parts = ["This is a local finance-agent draft, not professional financial advice."]
    if hits:
        parts.append(
            f"Right now I would treat this as review-needed: {len(hits)} active rule hit(s), "
            f"including {duplicate_count} duplicate-charge check(s), {high_count} high-transaction check(s), "
            f"and {uncategorized_count} categorization item(s)."
        )
    else:
        parts.append("No active rule hits are present in the latest local run.")

    if intent == "affordability":
        if amount is not None:
            parts.append(
                f"For a {_money(amount)} decision, I would not give a clean yes/no yet because the cash buffer "
                "and savings target are not fully configured."
            )
        else:
            parts.append(
                "For an affordability question, I need either the amount or a configured weekly/discretionary budget."
            )
        parts.append(
            f"Context: last 7 days spend is {_money(summary['last_7_days_spend'])}, "
            f"month-to-date spend is {_money(summary['month_to_date_spend'])}, "
            f"and the 30-day daily average is {_money(summary['average_daily_spend_30d'])}."
        )
        if hits:
            parts.append("Recommendation: review the active flags first, then decide on any optional spend.")
    elif intent == "alerts":
        parts.append(
            "The most useful alert criteria right now are duplicate charges, high transactions, unusual daily spend, "
            "and uncategorized transactions that block a budget review."
        )
    elif intent == "subscription":
        parts.append(
            "Recurring/subscription data appears limited in the local cache, so subscription answers may be incomplete until recurring items populate."
        )
    elif intent == "budget_health":
        budget_read = _budget_health_lines(suggested_category_spend, budget_config)
        parts.append(
            f"Budget health snapshot: month-to-date spend is {_money(summary['month_to_date_spend'])}; "
            f"last 30 days spend is {_money(summary['last_30_days_spend'])}; visible recent uncategorized count is {summary['recent_uncategorized_count']}."
        )
        parts.extend(budget_read)
    else:
        parts.append(
            f"Current context: today spend {_money(summary['today_spend'])}, "
            f"last 30 days {_money(summary['last_30_days_spend'])}, "
            f"recent uncategorized transactions {summary['recent_uncategorized_count']}."
        )

    if not cash_buffer_enabled or not savings_enabled:
        parts.append(
            "Next tuning step: define Patrick's cash buffer and savings target so the agent can answer with firmer criteria."
        )

    return "\n\n".join(parts)


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
    return round(float(row["spend"] or 0.0), 2)


def _uncategorized_count(conn: Any, start: date, end: date) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND amount > 0
          AND category_id IS NULL
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchone()
    return int(row["count"] or 0)


def _count(conn: Any, table: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
    return int(row["count"] or 0)


def _recent_transactions(
    conn: Any,
    start: date,
    end: date,
    *,
    limit: int,
    mapping_rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT t.date, t.payee, t.amount, t.status, t.is_pending, c.name AS category
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND t.amount > 0
        ORDER BY t.date DESC, t.id DESC
        LIMIT ?
        """,
        (start.isoformat(), end.isoformat(), limit),
    ).fetchall()
    return [
        {
            "date": row["date"],
            "payee": row["payee"] or "Unknown payee",
            "amount": row["amount"],
            "category": row["category"] or "Uncategorized",
            "status": row["status"],
            "pending": bool(row["is_pending"]),
            "suggestion": merchant_map.suggest_for_payee(row["payee"], mapping_rules),
        }
        for row in rows
    ]


def _top_payees(
    conn: Any,
    start: date,
    end: date,
    *,
    mapping_rules: list[dict[str, Any]],
    limit: int = 10,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT COALESCE(payee, original_name, 'Unknown payee') AS payee,
               ROUND(SUM(amount), 2) AS spend,
               COUNT(*) AS count
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND amount > 0
        GROUP BY COALESCE(payee, original_name, 'Unknown payee')
        ORDER BY spend DESC
        LIMIT ?
        """,
        (start.isoformat(), end.isoformat(), limit),
    ).fetchall()
    results = []
    for row in rows:
        item = dict(row)
        item["suggestion"] = merchant_map.suggest_for_payee(item["payee"], mapping_rules)
        results.append(item)
    return results


def _suggested_category_spend(
    conn: Any, start: date, end: date, mapping_rules: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not mapping_rules:
        return []
    rows = conn.execute(
        """
        SELECT COALESCE(payee, original_name, 'Unknown payee') AS payee,
               amount
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND amount > 0
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    totals: dict[str, dict[str, Any]] = {}
    for row in rows:
        suggestion = merchant_map.suggest_for_payee(row["payee"], mapping_rules)
        if not suggestion or not suggestion.get("category"):
            continue
        category = str(suggestion["category"])
        bucket = totals.setdefault(category, {"category": category, "spend": 0.0, "count": 0})
        bucket["spend"] += float(row["amount"] or 0.0)
        bucket["count"] += 1
    return sorted(
        [
            {"category": value["category"], "spend": round(value["spend"], 2), "count": value["count"]}
            for value in totals.values()
        ],
        key=lambda item: item["spend"],
        reverse=True,
    )


def _category_spend(conn: Any, start: date, end: date, *, limit: int = 10) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT COALESCE(c.name, 'Uncategorized') AS category,
               ROUND(SUM(t.amount), 2) AS spend,
               COUNT(*) AS count
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.date BETWEEN ? AND ?
          AND t.amount > 0
        GROUP BY COALESCE(c.name, 'Uncategorized')
        ORDER BY spend DESC
        LIMIT ?
        """,
        (start.isoformat(), end.isoformat(), limit),
    ).fetchall()
    return [dict(row) for row in rows]


def _account_summary(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT account_source,
               COALESCE(display_name, name, 'Unnamed account') AS name,
               type,
               balance,
               status
        FROM accounts
        ORDER BY account_source, name
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _criteria_summary(rules_config: dict[str, Any], budget_config: dict[str, Any]) -> dict[str, Any]:
    checks = rules_config.get("checks", {})
    budget = budget_config.get("budget", {})
    return {
        "high_transaction_threshold": checks.get("high_transaction", {}).get("threshold", 100.0),
        "duplicate_charge_window_days": checks.get("duplicate_charge", {}).get("window_days", 3),
        "unusual_daily_spend_multiplier": checks.get("unusual_daily_spend", {}).get("multiplier", 2.0),
        "cash_buffer_enabled": bool(budget.get("cash_buffer", {}).get("enabled", False)),
        "monthly_savings_target_enabled": bool(budget.get("monthly_savings_target", {}).get("enabled", False)),
        "discretionary_total_enabled": bool(budget.get("discretionary_total", {}).get("enabled", False)),
    }


def _clean_hit(hit: dict[str, Any]) -> dict[str, Any]:
    clean = dict(hit)
    try:
        clean["details"] = json.loads(clean.pop("details_json") or "{}")
    except json.JSONDecodeError:
        clean["details"] = {}
    return clean


def _classify_question(question: str) -> str:
    text = question.lower()
    if any(word in text for word in ["budget", "over budget", "under budget", "looking", "doing", "health"]):
        return "budget_health"
    if any(word in text for word in ["afford", "buy", "spend", "can i", "should i purchase"]):
        return "affordability"
    if any(word in text for word in ["alert", "alarm", "notify", "warn"]):
        return "alerts"
    if any(word in text for word in ["subscription", "recurring", "monthly charge"]):
        return "subscription"
    if any(word in text for word in ["duplicate", "double charge", "charged twice"]):
        return "duplicate_review"
    if any(word in text for word in ["category", "categorize", "uncategorized"]):
        return "categorization"
    return "general"


def _budget_health_lines(
    suggested_category_spend: list[dict[str, Any]], budget_config: dict[str, Any]
) -> list[str]:
    policies = {
        str(item.get("name")): item
        for item in budget_config.get("budget", {}).get("categories", [])
        if item.get("name")
    }
    over = []
    near = []
    for row in suggested_category_spend:
        category = str(row.get("category") or "")
        policy = policies.get(category)
        if not policy:
            continue
        limit = _as_float(policy.get("monthly_limit"))
        if not limit:
            continue
        spend = float(row.get("spend") or 0.0)
        ratio = spend / limit
        item = f"{category}: {_money(spend)} of {_money(limit)}"
        if ratio >= 1:
            over.append(f"{item}, over by {_money(spend - limit)}")
        elif ratio >= float(policy.get("warning_at_ratio", 0.85)):
            near.append(f"{item}, near limit")

    discretionary_policy = budget_config.get("budget", {}).get("discretionary_total", {})
    discretionary_limit = _as_float(discretionary_policy.get("monthly_limit"))
    discretionary_categories = {
        str(item.get("name"))
        for item in budget_config.get("budget", {}).get("categories", [])
        if item.get("discretionary") and item.get("name")
    }
    discretionary_spend = sum(
        float(row.get("spend") or 0.0)
        for row in suggested_category_spend
        if row.get("category") in discretionary_categories
    )

    lines = []
    if over:
        lines.append("Over configured limits: " + "; ".join(over[:5]) + ".")
    if near:
        lines.append("Near configured limits: " + "; ".join(near[:5]) + ".")
    if discretionary_limit:
        over_by = max(discretionary_spend - discretionary_limit, 0.0)
        if over_by > 0:
            lines.append(
                f"Discretionary total is over: {_money(discretionary_spend)} of {_money(discretionary_limit)}, over by {_money(over_by)}."
            )
        else:
            lines.append(
                f"Discretionary total is under limit: {_money(discretionary_spend)} of {_money(discretionary_limit)}."
            )
    if not lines:
        lines.append("No configured category limits are currently exceeded from the local suggested-category view.")
    lines.append("Best next action: review duplicate/high-signal alarms first, then tune category limits if the monthly limits feel unrealistic.")
    return lines


def _extract_amount(question: str) -> float | None:
    match = re.search(r"\$\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", question)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def _money(value: Any) -> str:
    if value is None:
        return "-"
    return f"${float(value):,.2f}"


def _escape_table(value: Any) -> str:
    return str(value or "").replace("|", "\\|")
