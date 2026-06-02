"""Markdown report generation for rule hits."""

from __future__ import annotations

import json
import shutil
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from . import storage


def write_report(
    db_path: Path,
    reports_root: Path,
    report_date: date,
    *,
    run_id: int | None = None,
    sample: bool = False,
    max_flagged_transactions: int = 40,
) -> Path:
    storage.init_db(db_path)
    run_id = run_id or storage.latest_rule_run_id(db_path, report_date)
    if run_id is None:
        raise RuntimeError("No rule run found. Run `python -m src.main check` first.")

    reports_root.mkdir(parents=True, exist_ok=True)
    daily_root = reports_root / "daily"
    daily_root.mkdir(parents=True, exist_ok=True)
    report_path = daily_root / f"{report_date.isoformat()}.md"
    latest_path = reports_root / "latest.md"

    markdown = build_markdown(
        db_path,
        report_date,
        run_id,
        sample=sample,
        max_flagged_transactions=max_flagged_transactions,
    )
    report_path.write_text(markdown, encoding="utf-8")
    shutil.copyfile(report_path, latest_path)
    return report_path


def build_markdown(
    db_path: Path,
    report_date: date,
    run_id: int,
    *,
    sample: bool = False,
    max_flagged_transactions: int = 40,
) -> str:
    with storage.connect(db_path) as conn:
        run = conn.execute("SELECT * FROM rule_runs WHERE id = ?", (run_id,)).fetchone()
        hits = conn.execute(
            "SELECT * FROM rule_hits WHERE run_id = ? ORDER BY severity DESC, rule_name, id",
            (run_id,),
        ).fetchall()
        snapshot_date = conn.execute("SELECT MAX(snapshot_date) AS snapshot_date FROM snapshots").fetchone()[
            "snapshot_date"
        ]
        summary = _summary(conn, report_date)
        transaction_hits = _flagged_transactions(conn, hits, max_flagged_transactions)

    hit_counts = Counter(hit["rule_name"] for hit in hits)
    sample_label = " [SAMPLE MOCK DATA]" if sample else ""
    lines: list[str] = [
        f"# Lunch Money Daily Finance Watcher{sample_label}",
        "",
        f"- Report date: {report_date.isoformat()}",
        f"- Snapshot date: {snapshot_date or 'none'}",
        f"- Rule run: {run_id}",
        f"- Generated at: {run['created_at'] if run else 'unknown'}",
        f"- Total rule hits: {len(hits)}",
        "",
    ]
    if sample:
        lines.extend(
            [
                "> This is a mocked sample report for reviewing format only. It is not Patrick's real financial data.",
                "",
            ]
        )

    lines.extend(
        [
            "## Summary",
            "",
            f"- Spend today: {_money(summary['today_spend'])}",
            f"- Spend month to date: {_money(summary['month_to_date_spend'])}",
            f"- Transactions in recent check window: {summary['recent_transaction_count']}",
            f"- Uncategorized recent transactions: {summary['recent_uncategorized_count']}",
            f"- Accounts stored: {summary['account_count']}",
            f"- Recurring items stored: {summary['recurring_count']}",
            "",
            "## Rule Hits",
            "",
        ]
    )

    if hit_counts:
        for rule_name, count in sorted(hit_counts.items()):
            lines.append(f"- {rule_name}: {count}")
    else:
        lines.append("- No rule hits.")
    lines.append("")

    lines.extend(["## Flagged Transactions", ""])
    if transaction_hits:
        lines.extend(
            [
                "| Date | Payee | Amount | Category | Rules |",
                "| --- | --- | ---: | --- | --- |",
            ]
        )
        for txn in transaction_hits:
            lines.append(
                "| {date} | {payee} | {amount} | {category} | {rules} |".format(
                    date=txn["date"],
                    payee=_escape_table(txn["payee"]),
                    amount=_money(txn["amount"]),
                    category=_escape_table(txn["category_name"] or "Uncategorized"),
                    rules=_escape_table(", ".join(txn["rules"])),
                )
            )
    else:
        lines.append("No flagged transaction-level items.")
    lines.append("")

    lines.extend(["## Detailed Rule Hits", ""])
    if hits:
        grouped: dict[str, list[Any]] = defaultdict(list)
        for hit in hits:
            grouped[hit["rule_name"]].append(hit)
        for rule_name, rule_hits in sorted(grouped.items()):
            lines.extend([f"### {rule_name}", ""])
            for hit in rule_hits:
                details = _details(hit)
                detail_text = _brief_details(details)
                suffix = f" ({detail_text})" if detail_text else ""
                amount = f" - {_money(hit['amount'])}" if hit["amount"] is not None else ""
                lines.append(f"- {hit['title']}{amount}{suffix}")
            lines.append("")
    else:
        lines.append("No detailed rule hits.")
        lines.append("")

    context = _chatgpt_context(report_date, sample, summary, hits, transaction_hits)
    lines.extend(
        [
            "## Needs ChatGPT Review",
            "",
            "Use this section as the handoff prompt for deeper analysis:",
            "",
            "```text",
            "Review this Lunch Money daily finance watcher report. Identify which items need action, which are likely noise, and what rule thresholds should be tuned. Keep the advice practical and local-first.",
            "```",
            "",
            "Structured context:",
            "",
            "```json",
            json.dumps(context, indent=2, sort_keys=True),
            "```",
            "",
            "## Open TODOs",
            "",
            "- define Patrick's actual alert thresholds",
            "- define categories considered discretionary",
            "- define merchants to ignore",
            "- define target monthly savings / cash buffer",
            "- decide whether to add OpenAI API automation",
            "- later build Streamlit dashboard",
            "",
        ]
    )

    return "\n".join(lines)


def _summary(conn: Any, report_date: date) -> dict[str, Any]:
    month_start = report_date.replace(day=1)
    recent_start = report_date - timedelta(days=2)
    today_spend = _spend_between(conn, report_date, report_date)
    month_spend = _spend_between(conn, month_start, report_date)
    recent = conn.execute(
        "SELECT COUNT(*) AS count FROM transactions WHERE date BETWEEN ? AND ?",
        (recent_start.isoformat(), report_date.isoformat()),
    ).fetchone()
    uncategorized = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM transactions
        WHERE date BETWEEN ? AND ?
          AND amount > 0
          AND category_id IS NULL
        """,
        (recent_start.isoformat(), report_date.isoformat()),
    ).fetchone()
    accounts = conn.execute("SELECT COUNT(*) AS count FROM accounts").fetchone()
    recurring = conn.execute("SELECT COUNT(*) AS count FROM recurring_items").fetchone()
    return {
        "today_spend": today_spend,
        "month_to_date_spend": month_spend,
        "recent_transaction_count": recent["count"],
        "recent_uncategorized_count": uncategorized["count"],
        "account_count": accounts["count"],
        "recurring_count": recurring["count"],
    }


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


def _flagged_transactions(conn: Any, hits: list[Any], limit: int) -> list[dict[str, Any]]:
    rules_by_transaction: dict[str, set[str]] = defaultdict(set)
    for hit in hits:
        if hit["entity_type"] == "transaction" and hit["entity_id"]:
            rules_by_transaction[str(hit["entity_id"])].add(hit["rule_name"])

    if not rules_by_transaction:
        return []

    placeholders = ",".join("?" for _ in rules_by_transaction)
    rows = conn.execute(
        f"""
        SELECT t.*, c.name AS category_name
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE CAST(t.id AS TEXT) IN ({placeholders})
        ORDER BY t.date DESC, t.amount DESC
        LIMIT ?
        """,
        (*rules_by_transaction.keys(), limit),
    ).fetchall()

    transactions = []
    for row in rows:
        txn_id = str(row["id"])
        transactions.append(
            {
                "id": txn_id,
                "date": row["date"],
                "payee": row["payee"] or row["original_name"] or "Unknown payee",
                "amount": row["amount"],
                "category_name": row["category_name"],
                "rules": sorted(rules_by_transaction[txn_id]),
            }
        )
    return transactions


def _chatgpt_context(
    report_date: date,
    sample: bool,
    summary: dict[str, Any],
    hits: list[Any],
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    flags_by_rule = Counter(hit["rule_name"] for hit in hits)
    return {
        "report_date": report_date.isoformat(),
        "sample_mock_data": sample,
        "summary": summary,
        "flags_by_rule": dict(sorted(flags_by_rule.items())),
        "flagged_transactions": transactions,
        "rule_hits": [
            {
                "rule": hit["rule_name"],
                "title": hit["title"],
                "entity_type": hit["entity_type"],
                "entity_id": hit["entity_id"],
                "date": hit["date"],
                "amount": hit["amount"],
                "payee": hit["payee"],
                "details": _details(hit),
            }
            for hit in hits
        ],
        "review_questions": [
            "Which flags are actionable versus expected?",
            "Which thresholds should be adjusted?",
            "Which merchants should be ignored?",
            "Which categories should be treated as discretionary?",
            "What belongs in a daily alert versus a future dashboard?",
        ],
    }


def _details(row: Any) -> dict[str, Any]:
    try:
        return json.loads(row["details_json"] or "{}")
    except json.JSONDecodeError:
        return {}


def _brief_details(details: dict[str, Any]) -> str:
    interesting_keys = [
        "threshold",
        "trailing_days",
        "trailing_average",
        "previous_amount",
        "latest_amount",
        "budgeted",
        "spending",
        "overspend_vs_pace",
    ]
    parts = []
    for key in interesting_keys:
        if key in details and details[key] is not None:
            parts.append(f"{key}: {details[key]}")
    return "; ".join(parts[:4])


def _money(value: Any) -> str:
    if value is None:
        return "-"
    return f"${float(value):,.2f}"


def _escape_table(value: Any) -> str:
    return str(value or "").replace("|", "\\|")
