# Execution evidence - Lakebase operational-serving layer

These are **real run logs** captured against the `zoccali-fevm-aws` workspace
(catalog `zoccali_fevm`, schema `energy_theft_protection`) on 2 Oct 2026. They
are committed as text so the build is verifiable without running anything.

## Files

| File | What it proves |
|------|----------------|
| [`lakebase_provision_run.txt`](lakebase_provision_run.txt) | End-to-end provisioning via `scripts/provision_lakebase.py`: deduped Delta serving source (327 rows), Lakebase instance `AVAILABLE`, synced table `ONLINE`, OLTP schema applied, a real open->close transaction, and verification counts. |
| [`lakebase_read_path_proof.txt`](lakebase_read_path_proof.txt) | The live read + write paths: top flagged accounts served from Postgres (synced from Delta gold), queue size by risk tier, the OLTP case row, and the append-only audit log produced by the state-transition trigger. |

## Verified facts

- **Synced table (Delta -> Postgres):** `energy_theft_protection.anomaly_scores_serving`
  holds **327** rows (HIGH **146**, MEDIUM **181**), synced from the Delta gold
  table. Sync reached `SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE`.
- **Instance:** `energy-theft-lakebase` (capacity `CU_1`) reached
  `AVAILABLE`; read-write DNS resolved and accepted a `psycopg` connection using
  a short-lived OAuth credential (no stored password).
- **OLTP write path:** a case was opened (`IN_PROGRESS`) and closed
  (`CONFIRMED_THEFT`, GBP 4,820 recovered) in Postgres with read-your-writes
  latency; the `BEFORE INSERT OR UPDATE` trigger appended **2** `case_events`
  rows (`CASE_OPENED`, `STATUS_CHANGE`) automatically.

## Reproduce

```bash
uv run python3 scripts/provision_lakebase.py \
  --profile zoccali-fevm-aws --catalog zoccali_fevm --warehouse-id 85c1b174d196486d
```

The script is idempotent: it reuses an existing instance / synced table and
re-applies the OLTP DDL with `IF NOT EXISTS` guards.
