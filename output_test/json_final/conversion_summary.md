# Tableau to Power BI Conversion Summary

**Report Name:** sample_superstore
**Conversion Date:** 2026-01-29 05:20:24 UTC
**Source:** samples/sample_superstore.twbx

## Files Generated

- **measures**: `output_test/json_final/measures.json`
- **model**: `output_test/json_final/model.json`
- **visuals**: `output_test/json_final/visuals.json`
- **dax**: `output_test/json_final/dax_measures.txt`

## Data Model Summary

| Component | Count |
|-----------|-------|
| Tables | 10 |
| Columns | 151 |
| Measures | 4 |
| Relationships | 1 |
| Pages | 1 |
| Visuals | 11 |

## How to Use These Files

### Option 1: Manual Creation in Power BI Desktop

1. Open Power BI Desktop
2. Connect to your data source
3. Open `dax_measures.txt` and copy each measure into Power BI
4. Create visuals based on `visuals.json`

### Option 2: Use the PBIP Format

The `.pbip` folder can be opened with Power BI Desktop (November 2023+)
with Developer Mode enabled.

### Option 3: Import Model via Tabular Editor

1. Download Tabular Editor (free)
2. Import `model.json` to create the semantic model
3. Connect to Power BI Service

## Measures Reference

### Orders (Sample-Superstore-Subset-Excel_0)

- ✅ **Gross Profit Ratio**
- ✅ **Number of Records**

### Parameters

- ⚠️ **Top Customers**
  - *Requires review*
- ⚠️ **Profit Bin Size**
  - *Requires review*
