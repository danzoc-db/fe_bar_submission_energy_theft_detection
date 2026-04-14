# Plan: Medallion Restructure, Two Jobs, and Bord Gáis Extension

## Two Jobs

### Job 1: Data Generation (Bronze → Silver → Gold → Metric Views)

| Task | Notebook | Description |
|------|----------|-------------|
| create_schema | `00_create_schema.py` | Drop/create schema and tables |
| bronze_ingest | `01a_bronze_ingest.py` | Raw synthetic data: property_reference, meters, smart_meter_reads, _ground_truth_labels |
| silver_cleanse | `01b_silver_cleanse.py` | Quality filtering, enrichment, validation |
| gold_aggregate | `01c_gold_aggregate.py` | Daily consumption, account features, cohort stats, model_performance_log |
| metric_views | `01d_metric_views.py` | UC Metric Views: theft_precision_rate, revenue_recovery |

### Job 2: ML Training, Scoring & Catalog Hydration

| Task | Notebook | Dependencies |
|------|----------|-------------|
| train_isolation_forest | `02_train_isolation_forest.py` | none (parallel) |
| train_lstm | `03_train_lstm_autoencoder.py` | none (parallel) |
| batch_scoring | `04_batch_scoring.py` | both training tasks |
| apply_uc_metadata | `05_apply_uc_metadata.py` | batch_scoring |

Job 2 runs after Job 1. Notebooks 02-04 updated to read from gold tables.
`05_apply_uc_metadata` runs last to hydrate UC with table/column comments, PII classification tags, and regulatory basis tags — required by Genie and the app's governance page.

## Medallion Layer Split

- **Bronze**: Raw generated data, `business_unit` column added to all tables
- **Silver**: Quality-filtered reads, validated postcodes, smart meters only
- **Gold**: Per-account features, daily aggregates, cohort stats (computed once, read by ML)
- **Metric Views**: UC Metric Views for Genie (theft precision rate, revenue recovery)

## Bord Gáis Energy Extension (via Genie Code)

### Why Bord Gáis

- Centrica's Irish retail brand, 514K+ customers, €72.5M operating profit (2025)
- ~1,500 suspected meter tampering cases/year in Ireland (ESB Networks)
- ~3,000 gas meter cases since 2013 (Gas Networks Ireland)
- Regulated by CRU (not Ofgem), MPRN (not MPAN), Eircode (not UK postcode), BER (not EPC)
- Proportional theft exposure ~€15-25M = 20-34% of operating profit

### Deliverables

| File | Purpose |
|------|---------|
| `docs/genie_code_prompt_bord_gais.md` | Prompt for Genie Code Agent mode |
| `docs/bord_gais_source_data.json` | Irish Eircodes, regions, BER ratings, property types |
| `notebooks/99_test_bord_gais.py` | Validation assertions |
| `notebooks/99_teardown_bord_gais.py` | Delete BGE data after testing |

### Workflow

1. Open notebook → Genie Code Agent mode → paste prompt
2. Genie Code generates `01a_bronze_ingest_bord_gais.py` (appends to existing tables with `business_unit = 'bord_gais'`)
3. Run generated notebook → silver/gold/metrics automatically pick up BGE data
4. Run `99_test_bord_gais.py` to validate
5. Run `99_teardown_bord_gais.py` to clean up
6. Keep only prompt + source data + test files in repo
