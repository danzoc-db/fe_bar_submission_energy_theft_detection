-- Energy Theft Detection — Unity Catalog DDL
-- Catalog: dz_demos | Schema: energy_theft_protection

CREATE SCHEMA IF NOT EXISTS dz_demos.energy_theft_protection
COMMENT 'British Gas Energy Theft Detection — AI anomaly detection demo. SIMULATED DATA.';

USE CATALOG dz_demos;
USE SCHEMA energy_theft_protection;

-- 1. Smart Meter Reads (half-hourly consumption)
CREATE OR REPLACE TABLE smart_meter_reads (
  account_id        STRING        COMMENT 'PII: ELEXON BSC — links to domestic customer',
  read_timestamp    TIMESTAMP     COMMENT 'Half-hourly interval',
  fuel_type         STRING        COMMENT 'electricity | gas',
  consumption_kwh   DOUBLE        COMMENT 'PII (when linked): Ofgem DAPF — personal when linked to MPAN',
  read_quality      STRING        COMMENT 'actual | estimated | missing',
  comms_gap_flag    BOOLEAN       COMMENT 'True if read is imputed due to comms gap',
  postcode          STRING        COMMENT 'PII: ICO — masked to sector level e.g. NW1 5',
  property_type     STRING        COMMENT 'terraced | semi-detached | detached | flat | bungalow',
  council_tax_band  STRING        COMMENT 'A–H'
)
COMMENT 'Half-hourly smart meter consumption readings. ~144M rows for 100K accounts × 48 reads/day × 30 days.'
TBLPROPERTIES ('demo.data_classification' = 'SIMULATED');

-- 2. Meters (meter registry)
CREATE OR REPLACE TABLE meters (
  meter_id              STRING    COMMENT 'Synthetic meter identifier',
  account_id            STRING    COMMENT 'PII: Links to domestic customer',
  mpan                  STRING    COMMENT 'PII: ELEXON BSC — Meter Point Administration Number',
  meter_serial_number   STRING    COMMENT 'PII: Ofgem — identifies physical device at premises',
  fuel_type             STRING    COMMENT 'electricity | gas',
  meter_type            STRING    COMMENT 'smart | traditional | prepayment',
  install_date          DATE      COMMENT 'Meter installation date',
  last_read_timestamp   TIMESTAMP COMMENT 'Timestamp of most recent read'
)
COMMENT 'Meter registry — ~200K meters (~2 per account).'
TBLPROPERTIES ('demo.data_classification' = 'SIMULATED');

-- 3. Anomaly Scores (ML-scored risk)
CREATE OR REPLACE TABLE anomaly_scores (
  account_id              STRING    COMMENT 'PII: Links scored risk to domestic customer',
  score_timestamp         TIMESTAMP COMMENT 'When scoring was performed',
  fuel_type               STRING    COMMENT 'electricity | gas',
  isolation_forest_score  DOUBLE    COMMENT '0–1, higher = more anomalous',
  lstm_deviation_score    DOUBLE    COMMENT 'Z-score vs own 90-day baseline',
  cohort_deviation_score  DOUBLE    COMMENT 'Z-score vs similar property cohort',
  comms_gap_count_30d     INT       COMMENT 'Communication gaps in last 30 days',
  consumption_drop_pct    DOUBLE    COMMENT 'Pct drop vs prior 30-day rolling avg',
  composite_risk_score    DOUBLE    COMMENT 'Weighted ensemble — PRIMARY signal',
  risk_tier               STRING    COMMENT 'HIGH | MEDIUM | LOW',
  postcode_sector         STRING    COMMENT 'PII: Identifies area of premises',
  model_version           STRING    COMMENT 'Model version used for scoring',
  investigation_status    STRING    COMMENT 'OPEN | IN_PROGRESS | CLOSED | CONFIRMED_THEFT'
)
COMMENT 'ML-scored risk per account. ~100K rows per scoring batch.'
TBLPROPERTIES ('demo.data_classification' = 'SIMULATED');

-- 4. Investigation Cases
CREATE OR REPLACE TABLE investigation_cases (
  case_id               STRING    COMMENT 'Unique case identifier',
  account_id            STRING    COMMENT 'PII: Links investigation to customer',
  opened_timestamp      TIMESTAMP COMMENT 'When case was opened',
  investigator_id       STRING    COMMENT 'PII (staff): Identifies British Gas employee',
  llm_summary           STRING    COMMENT 'PII (derived): Bedrock-generated summary may contain PII',
  field_dispatch_doc    STRING    COMMENT 'Field investigation document',
  outcome               STRING    COMMENT 'THEFT_CONFIRMED | FALSE_POSITIVE | PENDING',
  revenue_recovered_gbp DOUBLE    COMMENT 'GBP recovered from confirmed theft',
  closed_timestamp      TIMESTAMP COMMENT 'When case was closed (NULL if open)',
  region                STRING    COMMENT 'Geographic region'
)
COMMENT 'Investigation case lifecycle — ~5K cases.'
TBLPROPERTIES ('demo.data_classification' = 'SIMULATED');

-- 5. Property Reference
CREATE OR REPLACE TABLE property_reference (
  account_id       STRING    COMMENT 'PII: Links to domestic customer',
  postcode         STRING    COMMENT 'PII: Identifies premises',
  region           STRING    COMMENT 'UK region',
  property_type    STRING    COMMENT 'Quasi-PII with postcode',
  council_tax_band STRING    COMMENT 'Quasi-PII with postcode',
  floor_area_m2    DOUBLE    COMMENT 'Property floor area',
  epc_rating       STRING    COMMENT 'Quasi-PII: Linked to specific property via EPC register'
)
COMMENT 'Static property metadata — 100K rows.'
TBLPROPERTIES ('demo.data_classification' = 'SIMULATED');

-- 6. Model Performance Log
CREATE OR REPLACE TABLE model_performance_log (
  month             DATE      COMMENT 'Reporting month',
  model_version     STRING    COMMENT 'Model version',
  risk_tier         STRING    COMMENT 'HIGH | MEDIUM | LOW',
  precision_pct     DOUBLE    COMMENT 'Precision rate for this tier',
  recall_pct        DOUBLE    COMMENT 'Recall rate for this tier',
  f1_score          DOUBLE    COMMENT 'F1 score',
  cases_scored      INT       COMMENT 'Number of cases scored',
  cases_confirmed   INT       COMMENT 'Number of confirmed theft cases'
)
COMMENT 'Monthly model precision/recall/F1 metrics — ~24 rows.'
TBLPROPERTIES ('demo.data_classification' = 'SIMULATED');
