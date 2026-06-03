"""SQLite persistence for Lunch Money snapshots and normalized tables."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date TEXT NOT NULL,
    resource TEXT NOT NULL,
    raw_path TEXT,
    item_count INTEGER NOT NULL DEFAULT 0,
    api_version TEXT NOT NULL DEFAULT 'v2',
    fetched_at TEXT NOT NULL,
    warning TEXT,
    UNIQUE(snapshot_date, resource)
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT,
    to_base REAL,
    payee TEXT,
    original_name TEXT,
    category_id INTEGER,
    recurring_id INTEGER,
    status TEXT,
    is_pending INTEGER NOT NULL DEFAULT 0,
    manual_account_id INTEGER,
    plaid_account_id INTEGER,
    notes TEXT,
    source TEXT,
    raw_json TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    updated_at TEXT,
    created_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_payee_amount ON transactions(payee, amount);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    is_group INTEGER NOT NULL DEFAULT 0,
    group_name TEXT,
    is_income INTEGER NOT NULL DEFAULT 0,
    exclude_from_budget INTEGER NOT NULL DEFAULT 0,
    exclude_from_totals INTEGER NOT NULL DEFAULT 0,
    archived INTEGER NOT NULL DEFAULT 0,
    raw_json TEXT NOT NULL,
    snapshot_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    archived INTEGER NOT NULL DEFAULT 0,
    raw_json TEXT NOT NULL,
    snapshot_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    account_source TEXT NOT NULL,
    id INTEGER NOT NULL,
    name TEXT,
    display_name TEXT,
    institution_name TEXT,
    type TEXT,
    subtype TEXT,
    balance REAL,
    currency TEXT,
    status TEXT,
    raw_json TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    PRIMARY KEY (account_source, id)
);

CREATE TABLE IF NOT EXISTS recurring_items (
    id INTEGER PRIMARY KEY,
    payee TEXT,
    amount REAL,
    currency TEXT,
    category_id INTEGER,
    status TEXT,
    manual_account_id INTEGER,
    plaid_account_id INTEGER,
    raw_json TEXT NOT NULL,
    snapshot_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recurring_item_snapshots (
    snapshot_date TEXT NOT NULL,
    id INTEGER NOT NULL,
    payee TEXT,
    amount REAL,
    currency TEXT,
    category_id INTEGER,
    status TEXT,
    raw_json TEXT NOT NULL,
    PRIMARY KEY (snapshot_date, id)
);

CREATE TABLE IF NOT EXISTS budget_summary_categories (
    snapshot_date TEXT NOT NULL,
    category_id INTEGER NOT NULL,
    start_date TEXT,
    end_date TEXT,
    budgeted REAL,
    spending REAL,
    available REAL,
    currency TEXT,
    raw_json TEXT NOT NULL,
    PRIMARY KEY (snapshot_date, category_id, start_date, end_date)
);

CREATE TABLE IF NOT EXISTS rule_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    config_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rule_hits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES rule_runs(id) ON DELETE CASCADE,
    rule_name TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    date TEXT,
    amount REAL,
    payee TEXT,
    details_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rule_hits_run ON rule_hits(run_id);

CREATE TABLE IF NOT EXISTS one_number_ledger (
    month_key TEXT PRIMARY KEY,
    result REAL NOT NULL,
    daily_allowance REAL NOT NULL,
    discretionary_spend REAL NOT NULL,
    closed_at TEXT NOT NULL,
    details_json TEXT NOT NULL
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)


def save_pull_snapshot(
    db_path: Path,
    raw_root: Path,
    snapshot_date: date,
    payloads: dict[str, dict[str, Any]],
    warnings: Iterable[str] = (),
) -> None:
    init_db(db_path)
    raw_root.mkdir(parents=True, exist_ok=True)
    warning_map = _warning_map(warnings)
    fetched_at = utc_now()

    with connect(db_path) as conn:
        for resource, payload in payloads.items():
            raw_path = write_raw_snapshot(raw_root, snapshot_date, resource, payload)
            conn.execute(
                """
                INSERT INTO snapshots (
                    snapshot_date, resource, raw_path, item_count, api_version, fetched_at, warning
                )
                VALUES (?, ?, ?, ?, 'v2', ?, ?)
                ON CONFLICT(snapshot_date, resource) DO UPDATE SET
                    raw_path = excluded.raw_path,
                    item_count = excluded.item_count,
                    fetched_at = excluded.fetched_at,
                    warning = excluded.warning
                """,
                (
                    snapshot_date.isoformat(),
                    resource,
                    str(raw_path),
                    count_items(resource, payload),
                    fetched_at,
                    warning_map.get(resource),
                ),
            )

        upsert_transactions(conn, snapshot_date, _extract_list(payloads.get("transactions", {}), "transactions"))
        upsert_categories(conn, snapshot_date, _extract_list(payloads.get("categories", {}), "categories"))
        upsert_tags(conn, snapshot_date, _extract_list(payloads.get("tags", {}), "tags"))
        upsert_accounts(
            conn,
            snapshot_date,
            "manual",
            _extract_list(payloads.get("manual_accounts", {}), "manual_accounts"),
        )
        upsert_accounts(
            conn,
            snapshot_date,
            "plaid",
            _extract_list(payloads.get("plaid_accounts", {}), "plaid_accounts"),
        )
        upsert_recurring_items(
            conn,
            snapshot_date,
            _extract_list(payloads.get("recurring_items", {}), "recurring_items"),
        )
        upsert_budget_summary(
            conn,
            snapshot_date,
            payloads.get("budget_summary", {}),
        )
        conn.commit()


def write_raw_snapshot(
    raw_root: Path, snapshot_date: date, resource: str, payload: dict[str, Any]
) -> Path:
    daily_dir = raw_root / snapshot_date.isoformat()
    daily_dir.mkdir(parents=True, exist_ok=True)
    path = daily_dir / f"{resource}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def upsert_transactions(
    conn: sqlite3.Connection, snapshot_date: date, transactions: Iterable[dict[str, Any]]
) -> None:
    for txn in transactions:
        txn_id = _as_int(txn.get("id"))
        if txn_id is None:
            continue
        conn.execute(
            """
            INSERT INTO transactions (
                id, date, amount, currency, to_base, payee, original_name,
                category_id, recurring_id, status, is_pending, manual_account_id,
                plaid_account_id, notes, source, raw_json, snapshot_date, updated_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                date = excluded.date,
                amount = excluded.amount,
                currency = excluded.currency,
                to_base = excluded.to_base,
                payee = excluded.payee,
                original_name = excluded.original_name,
                category_id = excluded.category_id,
                recurring_id = excluded.recurring_id,
                status = excluded.status,
                is_pending = excluded.is_pending,
                manual_account_id = excluded.manual_account_id,
                plaid_account_id = excluded.plaid_account_id,
                notes = excluded.notes,
                source = excluded.source,
                raw_json = excluded.raw_json,
                snapshot_date = excluded.snapshot_date,
                updated_at = excluded.updated_at,
                created_at = excluded.created_at
            """,
            (
                txn_id,
                str(txn.get("date") or ""),
                _as_float(txn.get("to_base"), txn.get("amount"), default=0.0),
                txn.get("currency"),
                _as_float(txn.get("to_base")),
                txn.get("payee"),
                txn.get("original_name"),
                _as_int(txn.get("category_id")),
                _as_int(txn.get("recurring_id")),
                txn.get("status"),
                1 if txn.get("is_pending") else 0,
                _as_int(txn.get("manual_account_id")),
                _as_int(txn.get("plaid_account_id")),
                txn.get("notes"),
                txn.get("source"),
                _json(txn),
                snapshot_date.isoformat(),
                txn.get("updated_at"),
                txn.get("created_at"),
            ),
        )


def upsert_categories(
    conn: sqlite3.Connection, snapshot_date: date, categories: Iterable[dict[str, Any]]
) -> None:
    seen: set[int] = set()
    for category in flatten_categories(categories):
        category_id = _as_int(category.get("id") or category.get("category_id"))
        if category_id is None or category_id in seen:
            continue
        seen.add(category_id)
        conn.execute(
            """
            INSERT INTO categories (
                id, name, description, is_group, group_name, is_income,
                exclude_from_budget, exclude_from_totals, archived, raw_json, snapshot_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                description = excluded.description,
                is_group = excluded.is_group,
                group_name = excluded.group_name,
                is_income = excluded.is_income,
                exclude_from_budget = excluded.exclude_from_budget,
                exclude_from_totals = excluded.exclude_from_totals,
                archived = excluded.archived,
                raw_json = excluded.raw_json,
                snapshot_date = excluded.snapshot_date
            """,
            (
                category_id,
                str(category.get("name") or f"Category {category_id}"),
                category.get("description"),
                1 if category.get("is_group") else 0,
                category.get("group_name") or category.get("group_category_name"),
                1 if category.get("is_income") else 0,
                1 if category.get("exclude_from_budget") else 0,
                1 if category.get("exclude_from_totals") else 0,
                1 if category.get("archived") else 0,
                _json(category),
                snapshot_date.isoformat(),
            ),
        )


def upsert_tags(conn: sqlite3.Connection, snapshot_date: date, tags: Iterable[dict[str, Any]]) -> None:
    for tag in tags:
        tag_id = _as_int(tag.get("id"))
        if tag_id is None:
            continue
        conn.execute(
            """
            INSERT INTO tags (id, name, description, archived, raw_json, snapshot_date)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                description = excluded.description,
                archived = excluded.archived,
                raw_json = excluded.raw_json,
                snapshot_date = excluded.snapshot_date
            """,
            (
                tag_id,
                str(tag.get("name") or f"Tag {tag_id}"),
                tag.get("description"),
                1 if tag.get("archived") else 0,
                _json(tag),
                snapshot_date.isoformat(),
            ),
        )


def upsert_accounts(
    conn: sqlite3.Connection,
    snapshot_date: date,
    account_source: str,
    accounts: Iterable[dict[str, Any]],
) -> None:
    for account in accounts:
        account_id = _as_int(account.get("id"))
        if account_id is None:
            continue
        conn.execute(
            """
            INSERT INTO accounts (
                account_source, id, name, display_name, institution_name, type,
                subtype, balance, currency, status, raw_json, snapshot_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_source, id) DO UPDATE SET
                name = excluded.name,
                display_name = excluded.display_name,
                institution_name = excluded.institution_name,
                type = excluded.type,
                subtype = excluded.subtype,
                balance = excluded.balance,
                currency = excluded.currency,
                status = excluded.status,
                raw_json = excluded.raw_json,
                snapshot_date = excluded.snapshot_date
            """,
            (
                account_source,
                account_id,
                account.get("name"),
                account.get("display_name"),
                account.get("institution_name"),
                account.get("type") or account.get("type_name"),
                account.get("subtype") or account.get("subtype_name"),
                _as_float(account.get("to_base"), account.get("balance")),
                account.get("currency"),
                account.get("status"),
                _json(account),
                snapshot_date.isoformat(),
            ),
        )


def upsert_recurring_items(
    conn: sqlite3.Connection, snapshot_date: date, recurring_items: Iterable[dict[str, Any]]
) -> None:
    for item in recurring_items:
        recurring_id = _as_int(item.get("id"))
        if recurring_id is None:
            continue
        normalized = normalize_recurring_item(item)
        params = (
            recurring_id,
            normalized["payee"],
            normalized["amount"],
            normalized["currency"],
            normalized["category_id"],
            normalized["status"],
            normalized["manual_account_id"],
            normalized["plaid_account_id"],
            _json(item),
            snapshot_date.isoformat(),
        )
        conn.execute(
            """
            INSERT INTO recurring_items (
                id, payee, amount, currency, category_id, status,
                manual_account_id, plaid_account_id, raw_json, snapshot_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                payee = excluded.payee,
                amount = excluded.amount,
                currency = excluded.currency,
                category_id = excluded.category_id,
                status = excluded.status,
                manual_account_id = excluded.manual_account_id,
                plaid_account_id = excluded.plaid_account_id,
                raw_json = excluded.raw_json,
                snapshot_date = excluded.snapshot_date
            """,
            params,
        )
        conn.execute(
            """
            INSERT INTO recurring_item_snapshots (
                id, payee, amount, currency, category_id, status, raw_json, snapshot_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(snapshot_date, id) DO UPDATE SET
                payee = excluded.payee,
                amount = excluded.amount,
                currency = excluded.currency,
                category_id = excluded.category_id,
                status = excluded.status,
                raw_json = excluded.raw_json
            """,
            (
                recurring_id,
                normalized["payee"],
                normalized["amount"],
                normalized["currency"],
                normalized["category_id"],
                normalized["status"],
                _json(item),
                snapshot_date.isoformat(),
            ),
        )


def upsert_budget_summary(
    conn: sqlite3.Connection, snapshot_date: date, payload: dict[str, Any]
) -> None:
    for category in _extract_list(payload, "categories"):
        category_id = _as_int(category.get("category_id") or category.get("id"))
        if category_id is None:
            continue
        totals = category.get("totals") if isinstance(category.get("totals"), dict) else {}
        occurrences = category.get("occurrences")
        rows = occurrences if isinstance(occurrences, list) and occurrences else [totals]
        for row in rows:
            if not isinstance(row, dict):
                continue
            spending = _sum_numbers(row.get("other_activity"), row.get("recurring_activity"))
            budgeted = _as_float(row.get("budgeted"), row.get("budgeted_amount"))
            available = _as_float(row.get("available"))
            conn.execute(
                """
                INSERT INTO budget_summary_categories (
                    snapshot_date, category_id, start_date, end_date, budgeted,
                    spending, available, currency, raw_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(snapshot_date, category_id, start_date, end_date) DO UPDATE SET
                    budgeted = excluded.budgeted,
                    spending = excluded.spending,
                    available = excluded.available,
                    currency = excluded.currency,
                    raw_json = excluded.raw_json
                """,
                (
                    snapshot_date.isoformat(),
                    category_id,
                    row.get("start_date"),
                    row.get("end_date"),
                    budgeted,
                    spending,
                    available,
                    row.get("budgeted_currency"),
                    _json(category),
                ),
            )


def create_rule_run(db_path: Path, run_date: date, config: dict[str, Any]) -> int:
    init_db(db_path)
    with connect(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO rule_runs (run_date, created_at, config_json) VALUES (?, ?, ?)",
            (run_date.isoformat(), utc_now(), _json(config)),
        )
        conn.commit()
        return int(cursor.lastrowid)


def insert_rule_hits(db_path: Path, run_id: int, hits: Iterable[dict[str, Any]]) -> None:
    with connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO rule_hits (
                run_id, rule_name, severity, title, entity_type, entity_id,
                date, amount, payee, details_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    hit["rule_name"],
                    hit.get("severity", "info"),
                    hit["title"],
                    hit.get("entity_type"),
                    str(hit.get("entity_id")) if hit.get("entity_id") is not None else None,
                    hit.get("date"),
                    hit.get("amount"),
                    hit.get("payee"),
                    _json(hit.get("details", {})),
                )
                for hit in hits
            ],
        )
        conn.commit()


def latest_rule_run_id(db_path: Path, run_date: date | None = None) -> int | None:
    if not db_path.exists():
        return None
    sql = "SELECT id FROM rule_runs"
    params: tuple[Any, ...] = ()
    if run_date:
        sql += " WHERE run_date = ?"
        params = (run_date.isoformat(),)
    sql += " ORDER BY id DESC LIMIT 1"
    with connect(db_path) as conn:
        row = conn.execute(sql, params).fetchone()
    return int(row["id"]) if row else None


def latest_snapshot_date(db_path: Path) -> str | None:
    if not db_path.exists():
        return None
    with connect(db_path) as conn:
        row = conn.execute("SELECT MAX(snapshot_date) AS snapshot_date FROM snapshots").fetchone()
    return str(row["snapshot_date"]) if row and row["snapshot_date"] else None


def seed_mock_data(db_path: Path, report_date: date) -> None:
    """Create a small sample database for previewing the markdown report format."""

    init_db(db_path)
    previous_snapshot = report_date - timedelta(days=1)
    category_payload = {
        "categories": [
            {"id": 10, "name": "Groceries", "is_income": False, "exclude_from_budget": False, "exclude_from_totals": False},
            {"id": 11, "name": "Restaurants", "is_income": False, "exclude_from_budget": False, "exclude_from_totals": False},
            {"id": 12, "name": "Software", "is_income": False, "exclude_from_budget": False, "exclude_from_totals": False},
            {"id": 13, "name": "Transfers", "is_income": False, "exclude_from_budget": True, "exclude_from_totals": True},
        ]
    }
    manual_accounts = {
        "manual_accounts": [
            {"id": 100, "name": "Cash Wallet", "type": "cash", "balance": "75.00", "currency": "usd", "status": "active"}
        ]
    }
    plaid_accounts = {
        "plaid_accounts": [
            {"id": 200, "name": "Checking", "institution_name": "Sample Bank", "type": "depository", "balance": "5200.00", "currency": "usd", "status": "active"},
            {"id": 201, "name": "Credit Card", "institution_name": "Sample Card", "type": "credit", "balance": "812.43", "currency": "usd", "status": "active"},
        ]
    }

    prior_transactions = []
    for days_back in range(1, 96):
        txn_date = report_date - timedelta(days=days_back)
        prior_transactions.append(
            {
                "id": 10000 + days_back,
                "date": txn_date.isoformat(),
                "amount": "18.40",
                "currency": "usd",
                "to_base": 18.40,
                "payee": "Daily Market",
                "category_id": 10,
                "status": "reviewed",
                "is_pending": False,
                "plaid_account_id": 201,
                "source": "mock",
            }
        )
        if days_back % 7 == 0:
            prior_transactions.append(
                {
                    "id": 11000 + days_back,
                    "date": txn_date.isoformat(),
                    "amount": "43.25",
                    "currency": "usd",
                    "to_base": 43.25,
                    "payee": "Neighborhood Cafe",
                    "category_id": 11,
                    "status": "reviewed",
                    "is_pending": False,
                    "plaid_account_id": 201,
                    "source": "mock",
                }
            )

    current_transactions = [
        {
            "id": 20001,
            "date": report_date.isoformat(),
            "amount": "248.91",
            "currency": "usd",
            "to_base": 248.91,
            "payee": "New Camera Shop",
            "original_name": "NEW CAMERA SHOP 3344",
            "category_id": None,
            "status": "unreviewed",
            "is_pending": False,
            "plaid_account_id": 201,
            "source": "mock",
        },
        {
            "id": 20002,
            "date": report_date.isoformat(),
            "amount": "89.99",
            "currency": "usd",
            "to_base": 89.99,
            "payee": "Design Suite Pro",
            "category_id": 12,
            "recurring_id": 900,
            "status": "reviewed",
            "is_pending": False,
            "plaid_account_id": 201,
            "source": "mock",
        },
        {
            "id": 20003,
            "date": report_date.isoformat(),
            "amount": "36.44",
            "currency": "usd",
            "to_base": 36.44,
            "payee": "Corner Lunch",
            "category_id": 11,
            "status": "reviewed",
            "is_pending": False,
            "plaid_account_id": 201,
            "source": "mock",
        },
        {
            "id": 20004,
            "date": report_date.isoformat(),
            "amount": "36.44",
            "currency": "usd",
            "to_base": 36.44,
            "payee": "Corner Lunch",
            "category_id": 11,
            "status": "reviewed",
            "is_pending": False,
            "plaid_account_id": 201,
            "source": "mock",
        },
    ]

    old_recurring = {
        "recurring_items": [
            {
                "id": 900,
                "status": "reviewed",
                "transaction_criteria": {
                    "payee": "Design Suite Pro",
                    "amount": "69.99",
                    "currency": "usd",
                    "plaid_account_id": 201,
                },
                "overrides": {"category_id": 12},
            }
        ]
    }
    new_recurring = {
        "recurring_items": [
            {
                "id": 900,
                "status": "reviewed",
                "transaction_criteria": {
                    "payee": "Design Suite Pro",
                    "amount": "89.99",
                    "currency": "usd",
                    "plaid_account_id": 201,
                },
                "overrides": {"category_id": 12},
            }
        ]
    }
    budget_summary = {
        "aligned": True,
        "categories": [
            {
                "category_id": 11,
                "totals": {"other_activity": 250.88, "recurring_activity": 0, "budgeted": 200, "available": -50.88},
                "occurrences": [
                    {
                        "in_range": True,
                        "start_date": report_date.replace(day=1).isoformat(),
                        "end_date": _month_end(report_date).isoformat(),
                        "other_activity": 250.88,
                        "recurring_activity": 0,
                        "budgeted": 200,
                        "budgeted_amount": "200.0000",
                        "budgeted_currency": "usd",
                    }
                ],
            }
        ],
    }

    raw_root = db_path.parent / "raw-sample"
    save_pull_snapshot(
        db_path,
        raw_root,
        previous_snapshot,
        {
            "transactions": {"transactions": prior_transactions},
            "categories": category_payload,
            "manual_accounts": manual_accounts,
            "plaid_accounts": plaid_accounts,
            "recurring_items": old_recurring,
            "budget_summary": budget_summary,
            "budget_settings": {},
        },
    )
    save_pull_snapshot(
        db_path,
        raw_root,
        report_date,
        {
            "transactions": {"transactions": prior_transactions + current_transactions},
            "categories": category_payload,
            "manual_accounts": manual_accounts,
            "plaid_accounts": plaid_accounts,
            "recurring_items": new_recurring,
            "budget_summary": budget_summary,
            "budget_settings": {},
        },
    )


def flatten_categories(categories: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for category in categories:
        flattened.append(category)
        children = category.get("children")
        if isinstance(children, list):
            flattened.extend(flatten_categories([child for child in children if isinstance(child, dict)]))
    return flattened


def normalize_recurring_item(item: dict[str, Any]) -> dict[str, Any]:
    criteria = item.get("transaction_criteria") if isinstance(item.get("transaction_criteria"), dict) else {}
    overrides = item.get("overrides") if isinstance(item.get("overrides"), dict) else {}
    return {
        "payee": overrides.get("payee") or criteria.get("payee") or item.get("payee"),
        "amount": _as_float(criteria.get("to_base"), criteria.get("amount"), item.get("to_base"), item.get("amount")),
        "currency": criteria.get("currency") or item.get("currency"),
        "category_id": _as_int(overrides.get("category_id") or criteria.get("category_id") or item.get("category_id")),
        "status": item.get("status") or item.get("type"),
        "manual_account_id": _as_int(criteria.get("manual_account_id") or item.get("manual_account_id") or item.get("asset_id")),
        "plaid_account_id": _as_int(criteria.get("plaid_account_id") or item.get("plaid_account_id")),
    }


def count_items(resource: str, payload: dict[str, Any]) -> int:
    key_by_resource = {
        "transactions": "transactions",
        "categories": "categories",
        "manual_accounts": "manual_accounts",
        "plaid_accounts": "plaid_accounts",
        "recurring_items": "recurring_items",
        "tags": "tags",
    }
    key = key_by_resource.get(resource)
    if key:
        return len(_extract_list(payload, key))
    if isinstance(payload, dict) and payload:
        return 1
    return 0


def _extract_list(payload: dict[str, Any] | None, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key)
    if isinstance(value, dict):
        nested = value.get(key)
        if isinstance(nested, list):
            value = nested
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    items = payload.get("items")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


def _warning_map(warnings: Iterable[str]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for warning in warnings:
        resource = warning.split(":", 1)[0].strip()
        if resource:
            mapped[resource] = warning
    return mapped


def _as_float(*values: Any, default: float | None = None) -> float | None:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return default


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _sum_numbers(*values: Any) -> float | None:
    total = 0.0
    seen = False
    for value in values:
        number = _as_float(value)
        if number is not None:
            total += number
            seen = True
    return total if seen else None


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _month_end(day: date) -> date:
    if day.month == 12:
        return date(day.year, 12, 31)
    return date(day.year, day.month + 1, 1) - timedelta(days=1)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
