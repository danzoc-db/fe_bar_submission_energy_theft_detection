# Databricks notebook source
# MAGIC %md
# MAGIC # Energy Theft Detection — Apply Unity Catalog Metadata
# MAGIC
# MAGIC Applies column-level **comments**, **PII classification tags**, and **regulatory
# MAGIC basis tags** to every table in the schema.  Run this *after* all tables exist
# MAGIC (i.e. after notebooks 01 → 04 have completed).
# MAGIC
# MAGIC Tags are read back by the app's AI Governance page via `INFORMATION_SCHEMA`.

# COMMAND ----------

dbutils.widgets.text("catalog", "dz_demos")
dbutils.widgets.text("schema", "energy_theft_protection")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

print(f"Applying UC metadata to {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table comments

# COMMAND ----------

TABLE_COMMENTS = {
    "property_reference": "Customer property reference data — address, property type, EPC rating, and council tax band per account.",
    "meters": "Smart meter asset register — MPAN, serial number, fuel type, and installation details per meter.",
    "smart_meter_reads": "Half-hourly smart meter consumption reads — the primary data source for all downstream ML and analytics.",
    "anomaly_scores": "Composite ML risk scores per account — weighted ensemble of Isolation Forest, LSTM, and rule-based signals.",
    "investigation_cases": "Revenue protection investigation records — outcomes, LLM summaries, recovered revenue, and investigator assignment.",
    "model_performance_log": "Monthly model performance metrics — precision, recall, F1 by risk tier and model version.",
    "_ground_truth_labels": "Ground truth labels for model evaluation — known tampered vs normal accounts.",
}

for table, comment in TABLE_COMMENTS.items():
    try:
        spark.sql(f"COMMENT ON TABLE {table} IS '{comment}'")
        print(f"  ✓ {table}")
    except Exception as e:
        print(f"  ✗ {table}: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Column comments & PII tags
# MAGIC
# MAGIC Each entry in `COLUMN_METADATA` is `(table, column, comment, pii_tag, regulatory_basis)`.
# MAGIC `pii_tag` and `regulatory_basis` are `None` for non-PII columns (no tag applied).

# COMMAND ----------

COLUMN_METADATA = [
    # ── property_reference ──
    ("property_reference", "account_id",       "Unique customer account identifier — links to MPAN and premises",       "PII",       "ELEXON BSC — links to domestic customer"),
    ("property_reference", "postcode",         "Full UK postcode of customer premises",                                 "PII",       "ICO — identifies premises; masked to sector level downstream"),
    ("property_reference", "region",           "UK geographic region (e.g. London, South East)",                        None,        None),
    ("property_reference", "property_type",    "Type of dwelling (terraced, semi-detached, flat, etc.)",                None,        None),
    ("property_reference", "council_tax_band", "Council tax valuation band A–H",                                       None,        None),
    ("property_reference", "floor_area_m2",    "Approximate floor area in square metres",                              None,        None),
    ("property_reference", "epc_rating",       "Energy Performance Certificate rating A–G",                            None,        None),
    ("property_reference", "latitude",         "Approximate latitude of premises (jittered for demo)",                  "Quasi-PII", "ICO — combined with longitude can identify premises"),
    ("property_reference", "longitude",        "Approximate longitude of premises (jittered for demo)",                "Quasi-PII", "ICO — combined with latitude can identify premises"),

    # ── meters ──
    ("meters", "meter_id",             "Internal meter identifier",                                              None,        None),
    ("meters", "account_id",           "Links meter to customer account",                                        "PII",       "ELEXON BSC — links to domestic customer"),
    ("meters", "mpan",                 "Meter Point Administration Number — directly identifies premises",       "PII",       "ELEXON BSC — directly identifies premises"),
    ("meters", "meter_serial_number",  "Physical meter device serial number",                                    "PII",       "Ofgem — identifies physical device at premises"),
    ("meters", "fuel_type",            "Gas or electricity",                                                     None,        None),
    ("meters", "meter_type",           "Smart meter generation (SMETS1, SMETS2)",                                None,        None),
    ("meters", "install_date",         "Date the meter was installed",                                           None,        None),
    ("meters", "last_read_timestamp",  "Timestamp of the most recent meter read",                                None,        None),

    # ── smart_meter_reads ──
    ("smart_meter_reads", "account_id",        "Links consumption data to customer account",                          "PII",             "ELEXON BSC — links to domestic customer"),
    ("smart_meter_reads", "read_timestamp",    "Half-hourly read timestamp",                                          None,              None),
    ("smart_meter_reads", "fuel_type",         "Gas or electricity",                                                  None,              None),
    ("smart_meter_reads", "consumption_kwh",   "Half-hourly energy consumption in kWh — personal data when linked",   "PII",             "Ofgem DAPF — half-hourly data is personal when linked to MPAN/premises"),
    ("smart_meter_reads", "read_quality",      "Read quality flag: actual, estimated, or missing",                    None,              None),
    ("smart_meter_reads", "comms_gap_flag",    "True if the DCC communication link was interrupted",                  None,              None),
    ("smart_meter_reads", "postcode",          "Customer postcode (denormalised for feature engineering)",             "PII",             "ICO — identifies premises"),
    ("smart_meter_reads", "property_type",     "Property type (denormalised for cohort features)",                    None,              None),
    ("smart_meter_reads", "council_tax_band",  "Council tax band (denormalised for cohort features)",                 None,              None),

    # ── anomaly_scores ──
    ("anomaly_scores", "account_id",             "Links ML risk score to customer account",                           "PII",       "Links scored risk to domestic customer"),
    ("anomaly_scores", "score_timestamp",        "Timestamp when the ML scoring batch ran",                           None,        None),
    ("anomaly_scores", "fuel_type",              "Fuel type scored (electricity or gas)",                             None,        None),
    ("anomaly_scores", "isolation_forest_score", "Isolation Forest anomaly score (0–1, higher = more anomalous)",     None,        None),
    ("anomaly_scores", "lstm_deviation_score",   "LSTM autoencoder deviation score — temporal anomaly signal",        None,        None),
    ("anomaly_scores", "cohort_deviation_score", "Cohort deviation — how far this account deviates from similar properties", None, None),
    ("anomaly_scores", "comms_gap_count_30d",    "Count of DCC communication gaps in the last 30 days",              None,        None),
    ("anomaly_scores", "consumption_drop_pct",   "Percentage drop in consumption vs prior 30-day rolling average",   None,        None),
    ("anomaly_scores", "composite_risk_score",   "Weighted ensemble risk score (0–1) from all ML signals",           None,        None),
    ("anomaly_scores", "risk_tier",              "Risk classification: HIGH (≥0.75), MEDIUM (≥0.50), LOW (<0.50)",   None,        None),
    ("anomaly_scores", "postcode_sector",        "Postcode sector (e.g. E1 4) — identifies geographic area",         "PII",       "Identifies area of premises"),
    ("anomaly_scores", "model_version",          "Combined model version string (e.g. if_v3_lstm_v3)",               None,        None),
    ("anomaly_scores", "investigation_status",   "Current investigation status: OPEN, IN_PROGRESS, CLOSED",          None,        None),

    # ── investigation_cases ──
    ("investigation_cases", "case_id",               "Unique investigation case reference",                                          None,             None),
    ("investigation_cases", "account_id",            "Links investigation to customer account",                                      "PII",            "Links investigation to customer"),
    ("investigation_cases", "opened_timestamp",      "Timestamp when the investigation was opened",                                  None,             None),
    ("investigation_cases", "investigator_id",       "Assigned investigator employee ID",                                            "PII (staff)",    "Identifies UKI Gas employee"),
    ("investigation_cases", "llm_summary",           "LLM-generated case summary — may contain account-linked PII from prompt",     "PII (derived)",  "LLM output may contain account-linked PII from prompt context"),
    ("investigation_cases", "field_dispatch_doc",    "LLM-generated field dispatch document",                                       "PII (derived)",  "LLM output may reference account details"),
    ("investigation_cases", "outcome",               "Investigation outcome: THEFT_CONFIRMED, FALSE_POSITIVE, or PENDING",          None,             None),
    ("investigation_cases", "revenue_recovered_gbp", "Revenue recovered through back-billing (GBP)",                                None,             None),
    ("investigation_cases", "closed_timestamp",      "Timestamp when the investigation was closed (null if pending)",                None,             None),
    ("investigation_cases", "region",                "Geographic region of the investigated account",                                None,             None),

    # ── model_performance_log ──
    ("model_performance_log", "month",           "Calendar month of the performance measurement",                       None, None),
    ("model_performance_log", "model_version",   "ML model version identifier",                                         None, None),
    ("model_performance_log", "risk_tier",       "Risk tier being measured (HIGH or MEDIUM)",                            None, None),
    ("model_performance_log", "precision_pct",   "Precision: confirmed theft / total flagged (%)",                       None, None),
    ("model_performance_log", "recall_pct",      "Recall: confirmed theft / total actual theft (%)",                     None, None),
    ("model_performance_log", "f1_score",        "F1 score: harmonic mean of precision and recall",                      None, None),
    ("model_performance_log", "cases_scored",    "Number of cases scored in this tier and month",                        None, None),
    ("model_performance_log", "cases_confirmed", "Number of confirmed theft cases",                                     None, None),

    # ── _ground_truth_labels ──
    ("_ground_truth_labels", "account_id",   "Links ground truth label to customer account", "PII", "Links label to domestic customer"),
    ("_ground_truth_labels", "is_tampered",  "Whether the account is known to be tampered",  None,  None),
    ("_ground_truth_labels", "label_type",   "Type of ground truth label (normal, tampered)", None, None),
]

# COMMAND ----------

# MAGIC %md
# MAGIC ### Apply column comments

# COMMAND ----------

for table, column, comment, _, _ in COLUMN_METADATA:
    safe_comment = comment.replace("'", "\\'")
    try:
        spark.sql(f"ALTER TABLE {table} ALTER COLUMN {column} COMMENT '{safe_comment}'")
    except Exception as e:
        print(f"  ✗ comment {table}.{column}: {e}")

print("Column comments applied")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Apply PII classification & regulatory basis tags

# COMMAND ----------

pii_entries = [(t, c, tag, reg) for t, c, _, tag, reg in COLUMN_METADATA if tag is not None]
print(f"Applying tags to {len(pii_entries)} PII columns...")

for table, column, pii_tag, regulatory_basis in pii_entries:
    safe_tag = pii_tag.replace("'", "\\'")
    safe_reg = regulatory_basis.replace("'", "\\'")
    try:
        spark.sql(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"SET TAGS ('pii_classification' = '{safe_tag}', 'regulatory_basis' = '{safe_reg}')"
        )
        print(f"  ✓ {table}.{column} → {pii_tag}")
    except Exception as e:
        print(f"  ✗ {table}.{column}: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Verify tags via INFORMATION_SCHEMA

# COMMAND ----------

df_tags = spark.sql(f"""
    SELECT
        table_name,
        column_name,
        tag_name,
        tag_value
    FROM {CATALOG}.information_schema.column_tags
    WHERE schema_name = '{SCHEMA}'
      AND tag_name IN ('pii_classification', 'regulatory_basis')
    ORDER BY table_name, column_name, tag_name
""")

display(df_tags)
print(f"\nTotal tagged column-tag pairs: {df_tags.count()}")
