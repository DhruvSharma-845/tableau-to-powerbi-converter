# Tableau to Power BI Conversion Report

**Workbook:** complex_lod_expressions
**Generated:** 2026-01-27T23:21:08.819935
**Overall Success Rate:** 87.5%

---

## Summary

| Component | Total | Successful | Warnings | Errors | Success Rate |
|-----------|-------|------------|----------|--------|--------------|
| Formulas | 17 | 17 | 17 | 0 | 100.0% |
| Visuals | 4 | 3 | 1 | 0 | 75.0% |
| Data Sources | 1 | 1 | 0 | 0 | 100.0% |
| Parameters | 2 | 0 | 2 | 0 | 0.0% |

---

## Issues Requiring Attention

### 🟡 WARNING

- **Formula Translation** - Total Sales (FIXED)
  - Medium confidence translation - verify behavior
  - *Suggestion:* Compare output values with Tableau for sample data

- **Formula Translation** - Customer Total Sales
  - Medium confidence translation - verify behavior
  - *Suggestion:* Compare output values with Tableau for sample data

- **Formula Translation** - Region-Category Sales
  - Medium confidence translation - verify behavior
  - *Suggestion:* Compare output values with Tableau for sample data

- **Formula Translation** - Customer First Order Date
  - Medium confidence translation - verify behavior
  - *Suggestion:* Compare output values with Tableau for sample data

- **Formula Translation** - Avg Order Value per Customer
  - Medium confidence translation - verify behavior
  - *Suggestion:* Compare output values with Tableau for sample data

- **Formula Translation** - Sales Including City
  - Medium confidence translation - verify behavior
  - *Suggestion:* Compare output values with Tableau for sample data

- **Formula Translation** - Avg Sales Including Product
  - Medium confidence translation - verify behavior
  - *Suggestion:* Compare output values with Tableau for sample data

- **Formula Translation** - Daily Order Count
  - Medium confidence translation - verify behavior
  - *Suggestion:* Compare output values with Tableau for sample data

- **Formula Translation** - Sales Excluding State
  - Medium confidence translation - verify behavior
  - *Suggestion:* Compare output values with Tableau for sample data

- **Formula Translation** - Sales Excluding Product
  - Medium confidence translation - verify behavior
  - *Suggestion:* Compare output values with Tableau for sample data

- **Formula Translation** - Avg Sales Excluding City
  - Medium confidence translation - verify behavior
  - *Suggestion:* Compare output values with Tableau for sample data

- **Formula Translation** - Customer % of Total
  - Medium confidence translation - verify behavior
  - *Suggestion:* Compare output values with Tableau for sample data

- **Formula Translation** - Region Share in Category
  - Medium confidence translation - verify behavior
  - *Suggestion:* Compare output values with Tableau for sample data

- **Formula Translation** - New Customer Sales
  - Medium confidence translation - verify behavior
  - *Suggestion:* Compare output values with Tableau for sample data

- **Formula Translation** - Is Repeat Customer
  - Medium confidence translation - verify behavior
  - *Suggestion:* Compare output values with Tableau for sample data

- **Formula Translation** - Is Top Customer
  - Medium confidence translation - verify behavior
  - *Suggestion:* Compare output values with Tableau for sample data

- **Formula Translation** - Cohort Total Sales
  - Medium confidence translation - verify behavior
  - *Suggestion:* Compare output values with Tableau for sample data

- **Visual Mapping** - Regional Performance
  - Partial mapping - some features may not translate
  - *Suggestion:* Size encoding not supported for this visual type

- **Parameter** - Date Granularity
  - Parameters require manual setup in Power BI
  - *Suggestion:* Create as What-If parameter or slicer (type: list)

- **Parameter** - Top N
  - Parameters require manual setup in Power BI
  - *Suggestion:* Create as What-If parameter or slicer (type: range)

- **Dashboard Action** - LOD Analysis Dashboard
  - Action 'Filter by Customer' requires manual setup
  - *Suggestion:* Configure as Power BI drillthrough or cross-filter

- **Dashboard Action** - LOD Analysis Dashboard
  - Action 'Highlight Region' requires manual setup
  - *Suggestion:* Configure as Power BI drillthrough or cross-filter

### 🔵 INFO

- **Unmapped Feature** - Regional Performance
  - Feature not mapped: Size field: Sales.SalesData].[Calculation_SalesExcludeState

---

## Formula Translations

### Translation Summary
- High confidence: 0
- Medium confidence: 17
- Low confidence: 0
- Failed: 0

---

## Recommendations

- Found 2 parameter(s). Create these as What-If parameters or slicers in Power BI. The generated measures reference parameter tables that need to be created.
- Moderate success rate. Plan for some manual adjustment work, especially for complex calculations and visualizations.
