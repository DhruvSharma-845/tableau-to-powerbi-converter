# Tableau to Power BI Converter

A Python tool for converting Tableau workbooks (.twbx/.twb) to Power BI reports using the PBIR format.

## Features

- Parse Tableau workbook files (TWBX/TWB)
- Extract data sources, calculated fields, visualizations, and dashboards
- Translate Tableau formulas to DAX using GenAI
- Generate Power BI PBIR format output
- Batch conversion support for enterprise migrations
- Validation reports for translation accuracy

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Single File Conversion

```bash
python main.py convert path/to/workbook.twbx -o output/
```

### Batch Conversion

```bash
python main.py batch path/to/workbooks/ -o output/
```

### Generate Validation Report

```bash
python main.py validate path/to/workbook.twbx
```

## Environment Variables

- `OPENAI_API_KEY`: Required for GenAI-powered formula translation

## Architecture

```
tableau-to-powerbi-converter/
├── models/              # Data model classes
├── parsers/             # TWBX/TWB parsing
├── translators/         # Formula and visual translation
├── generators/          # PBIR output generation
├── main.py              # CLI entry point
└── requirements.txt
```

## Limitations

- Table calculations with complex addressing may require manual review
- Some Tableau visuals have no direct Power BI equivalent
- Dashboard actions need manual configuration
- Row-level security requires manual setup

## License

MIT
