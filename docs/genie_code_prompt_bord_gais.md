# Genie Code Prompt — Bord Gáis Energy Bronze Ingest

Paste the following prompt into a Databricks notebook in **Genie Code Agent mode** to
generate a bronze ingest notebook for Bord Gáis Energy (Centrica's Irish retail brand).

---

## Prompt

```
Create a Databricks notebook called `01a_bronze_ingest_bord_gais.py` that generates
synthetic smart meter data for Bord Gáis Energy and APPENDS it to existing tables in
the `energy_theft_protection` schema. Do NOT overwrite — use mode("append").

### Context

The schema already contains British Gas data with `business_unit = 'british_gas'`.
This notebook adds Irish data with `business_unit = 'bord_gais'`.

### Parameters

- Widgets: `catalog` (default "dz_demos"), `schema` (default "energy_theft_protection")
- BUSINESS_UNIT = "bord_gais"
- NUM_ACCOUNTS = 500 (prefix accounts BGE-XXXXXXX)
- TAMPERED_PCT = 0.04 (slightly higher — Ireland has proportionally more cases)
- DAYS_OF_READS = 90
- SAMPLE_FACTOR = 6

### Tables to append to

1. **property_reference** — same schema as existing but use:
   - Irish Eircodes (e.g. D01, D02, D04, D08, T12, T23, P31, H91, V94, N37, R95, F94)
   - Irish regions: Dublin, Cork, Galway, Limerick, Waterford, Kerry, Wexford, Donegal, Mayo, Sligo, Louth
   - BER ratings (A1-G) instead of EPC ratings — column name stays `epc_rating` for compatibility
   - Irish property types: terraced, semi-detached, detached, apartment, bungalow
   - No council_tax_band in Ireland — use LPT bands: 1-19 (as strings)
   - Latitude/longitude for Irish cities

2. **meters** — same schema but use:
   - MPRN (Meter Point Reference Number) instead of MPAN — store in the `mpan` column for compatibility
   - meter_type distribution: smart 60%, traditional 30%, prepayment 10%

3. **smart_meter_reads** — identical schema, Irish Eircodes in postcode column

4. **_ground_truth_labels** — identical schema

### Irish-specific data

Load Eircode prefixes and coordinates from `docs/bord_gais_source_data.json` in the
repo (available in the workspace at the notebook's level). Parse it with:
```python
import json
with open("../docs/bord_gais_source_data.json") as f:
    irish_data = json.load(f)
```

### Tamper patterns

Use the same three tamper types (A: sudden drop, B: gradual decline, C: intermittent)
with the same parameter ranges as the British Gas notebook.

### Important

- All DataFrames must include `business_unit = 'bord_gais'` column
- Use `.write.mode("append")` — never overwrite
- After writing, print row counts for each table showing both business units:
  `spark.sql("SELECT business_unit, COUNT(*) FROM table GROUP BY business_unit")`
```

---

## Expected output

Genie Code generates a complete `01a_bronze_ingest_bord_gais.py` notebook that:
1. Reads Irish reference data from `docs/bord_gais_source_data.json`
2. Generates 500 accounts with Irish-specific properties
3. Appends to all four bronze tables
4. The silver views and gold aggregations automatically include Bord Gáis data
