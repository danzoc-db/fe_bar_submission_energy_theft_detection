# Execution evidence - connected six-stage journey

Real run output captured against workspace profile `zoccali-fevm-aws`
(catalog `zoccali_fevm`, schema `energy_theft_protection`) on 2 Oct 2026.
Source code alone is not the proof; these logs are.

Journey the `end_to_end` job now encodes:

    Lakeflow -> Unity Catalog -> ML scoring -> Lakebase -> Genie -> App

Task `provision_lakebase` (`notebooks/10_provision_lakebase.py`) runs after
`batch_scoring` and is a dependency of `configure_genie`.

## Files

| File | Stage | What it proves |
|------|-------|----------------|
| [`end_to_end_journey.txt`](end_to_end_journey.txt) | 1-6 connected | One log: medallion row counts, UC comments + table lineage, ML precision by month, Lakebase ONLINE + OLTP counts, Genie Q-to-SQL-to-answer on a Metric View, deployed app with `lakebase` resource. |
| [`lakebase_provision_run.txt`](lakebase_provision_run.txt) | 4 | Instance AVAILABLE, synced table ONLINE, 327 queue rows, OLTP open/close + trigger. |
| [`lakebase_read_path_proof.txt`](lakebase_read_path_proof.txt) | 4 | Postgres serving queue (HIGH/MEDIUM) and case audit trail. |

## Verified facts (2 Oct 2026)

- **Lakeflow:** `smart_meter_reads` 2,793,758; `anomaly_scores` 1,815 (HIGH 146 / MEDIUM 181 / LOW 1,488); serving source and synced table both 327.
- **UC:** table comments on gold/ML tables; `system.access.table_lineage` shows Metric View materialisations from `theft_detection_metrics`.
- **ML:** latest HIGH-tier `model_performance_log` (2026-09) precision 81.9 / recall 82.0 / F1 82.0.
- **Lakebase:** `energy-theft-lakebase` CU_1 AVAILABLE; sync `SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE`; Postgres queue 327; OLTP cases 7 / events 9.
- **Genie:** question "year-to-date revenue recovered from confirmed theft" generated

      SELECT MEASURE(`Revenue Recovered`) ...
      FROM zoccali_fevm.energy_theft_protection.theft_detection_metrics

  and answered GBP 119.4m YTD (synthetic demo data).
- **App:** ACTIVE, deployment SUCCEEDED, resources include `lakebase` + `genie-space`.

## Reproduce

```bash
uv run python3 scripts/capture_journey_evidence.py \
  --profile zoccali-fevm-aws --catalog zoccali_fevm \
  --warehouse-id 85c1b174d196486d \
  --genie-space-id 01f16db6c03419a3b953033d66b5855f
```

The `end_to_end` Databricks Job is the scheduled connected run; this script is
the committable snapshot of the same six stages on the live workspace.
