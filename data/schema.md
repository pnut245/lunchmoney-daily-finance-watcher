# SQLite Schema

Database path: `data/lunchmoney.db`

## `snapshots`

One row per pulled resource per day. Tracks snapshot date, resource name, raw JSON path, item count, API version, fetch timestamp, and optional warning.

## `transactions`

Normalized transaction table keyed by Lunch Money transaction `id`.

Important fields:

- `date`
- `amount`: base spend amount when `to_base` is available, otherwise API `amount`
- `currency`
- `payee`
- `original_name`
- `category_id`
- `recurring_id`
- `status`
- `is_pending`
- `manual_account_id`
- `plaid_account_id`
- `raw_json`

Lunch Money v2 represents positive amounts as debits/spend and negative amounts as credits/inflow.

## `categories`

Normalized category cache keyed by category `id`. Includes income/exclusion flags so spend checks can ignore income and transfer-style categories when Lunch Money marks them excluded from totals.

The watcher tries v2 `/categories` first and falls back to read-only v1 `/categories` when v2 returns an empty list.

## `tags`

Normalized tag/label cache keyed by tag `id`.

The watcher currently uses read-only v1 `/tags` for this cache because tags are part of the legacy API surface.

## `accounts`

Combined account cache for manual and Plaid accounts.

Primary key:

- `account_source`: `manual` or `plaid`
- `id`

## `recurring_items`

Current normalized recurring item cache keyed by recurring item `id`.

## `recurring_item_snapshots`

Historical recurring item snapshots keyed by `(snapshot_date, id)`. This lets `recurring_amount_change` compare the newest pull with the previous pull.

## `budget_summary_categories`

Normalized category-level budget summary rows from the v2 `/summary` endpoint when available.

Used by the `category_budget_pacing` rule.

## `rule_runs`

One row per check run. Stores run date, creation timestamp, and the JSON-serialized rules config used for that run.

## `rule_hits`

One row per rule/anomaly hit.

Important fields:

- `run_id`
- `rule_name`
- `severity`
- `title`
- `entity_type`
- `entity_id`
- `date`
- `amount`
- `payee`
- `details_json`
