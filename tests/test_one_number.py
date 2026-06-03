from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from src import one_number, storage


class OneNumberTests(unittest.TestCase):
    def test_today_state_uses_allowance_minus_non_excluded_spend(self) -> None:
        run_date = date(2026, 6, 2)
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            _seed_one_number_db(db_path, run_date)

            state = one_number.build_state(
                db_path,
                {
                    "one_number": {
                        "daily_allowance": 55,
                        "excluded_categories": ["Transfers", "Utilities"],
                        "excluded_payees": ["Ignored Store"],
                    }
                },
                run_date,
                last_updated="2026-06-02T23:00:00",
            )

        self.assertEqual(state["daily_allowance"], 55)
        self.assertEqual(state["today_discretionary_spend"], 18)
        self.assertEqual(state["remaining_today"], 37)
        self.assertFalse(state["is_negative"])
        self.assertEqual(state["last_updated"], "2026-06-02T23:00:00")

    def test_negative_state_when_spend_exceeds_allowance(self) -> None:
        run_date = date(2026, 6, 2)
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            _seed_one_number_db(db_path, run_date)

            state = one_number.build_state(
                db_path,
                {
                    "one_number": {
                        "daily_allowance": 10,
                        "excluded_categories": ["Transfers", "Utilities"],
                        "excluded_payees": ["Ignored Store"],
                    }
                },
                run_date,
            )

        self.assertEqual(state["today_discretionary_spend"], 18)
        self.assertEqual(state["remaining_today"], -8)
        self.assertTrue(state["is_negative"])

    def test_close_month_stores_ledger_entry(self) -> None:
        run_date = date(2026, 6, 2)
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            _seed_one_number_db(db_path, run_date)

            entry = one_number.close_month(
                db_path,
                {
                    "one_number": {
                        "daily_allowance": 55,
                        "excluded_categories": ["Transfers", "Utilities"],
                        "excluded_payees": ["Ignored Store"],
                    }
                },
                run_date,
                closed_at="2026-07-01T00:00:00",
            )
            ledger = one_number.ledger_entries(db_path)

        self.assertEqual(entry["month"], "2026-06")
        self.assertEqual(entry["daily_allowance"], 55)
        self.assertEqual(entry["discretionary_spend"], 18)
        self.assertEqual(entry["result"], 1632)
        self.assertEqual(ledger[0]["month"], "2026-06")
        self.assertEqual(ledger[0]["result"], 1632)


def _seed_one_number_db(db_path: Path, run_date: date) -> None:
    storage.init_db(db_path)
    payloads = {
        "categories": {
            "categories": [
                {"id": 1, "name": "Restaurants", "is_income": False},
                {"id": 2, "name": "Transfers", "is_income": False},
                {"id": 3, "name": "Utilities", "is_income": False},
            ]
        },
        "transactions": {
            "transactions": [
                {
                    "id": 1,
                    "date": run_date.isoformat(),
                    "amount": "18.00",
                    "payee": "Lunch Place",
                    "category_id": 1,
                    "status": "reviewed",
                    "is_pending": False,
                },
                {
                    "id": 2,
                    "date": run_date.isoformat(),
                    "amount": "100.00",
                    "payee": "Bank Transfer",
                    "category_id": 2,
                    "status": "reviewed",
                    "is_pending": False,
                },
                {
                    "id": 3,
                    "date": run_date.isoformat(),
                    "amount": "22.00",
                    "payee": "Ignored Store",
                    "category_id": 1,
                    "status": "reviewed",
                    "is_pending": False,
                },
                {
                    "id": 4,
                    "date": run_date.isoformat(),
                    "amount": "44.00",
                    "payee": "Pending Cafe",
                    "category_id": 1,
                    "status": "pending",
                    "is_pending": True,
                },
                {
                    "id": 5,
                    "date": run_date.isoformat(),
                    "amount": "-12.00",
                    "payee": "Refund",
                    "category_id": 1,
                    "status": "reviewed",
                    "is_pending": False,
                },
            ]
        },
        "manual_accounts": {"manual_accounts": []},
        "plaid_accounts": {"plaid_accounts": []},
        "recurring_items": {"recurring_items": []},
        "budget_summary": {"categories": []},
    }
    storage.save_pull_snapshot(db_path, db_path.parent / "raw", run_date, payloads)


if __name__ == "__main__":
    unittest.main()
