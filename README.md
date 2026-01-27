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

## Converting to PBIX (Mac/Linux Users)

Since Power BI Desktop only runs on Windows, Mac/Linux users can use **GitHub Actions** (free) to convert PBIP to PBIX in the cloud.

### Option 1: GitHub Actions (Recommended - No Windows Required!)

This repo includes GitHub Action workflows that run on free Windows runners:

1. **Push your code to GitHub:**
   ```bash
   git add .
   git commit -m "Add conversion files"
   git push
   ```

2. **Run the conversion workflow:**
   - Go to your repo on GitHub
   - Click **Actions** tab
   - Select **"Convert Tableau to Power BI"**
   - Click **"Run workflow"**
   - Enter your Tableau file path (e.g., `samples/sample_superstore.twbx`)
   - Click **"Run workflow"**

3. **Download your PBIX:**
   - Wait for the workflow to complete (~2-3 minutes)
   - Click on the completed run
   - Scroll down to **"Artifacts"**
   - Download `powerbi-conversion-results`

The ZIP file contains:
- `.pbip` folder (Power BI Project format)
- `.pbix` file (if pbi-tools conversion succeeded)
- Validation report

### Option 2: Power BI Desktop on Windows

If you have access to Windows:

The converter generates **PBIP** (Power BI Project) format by default. To convert to **PBIX** format, you need to use the Power BI Service REST API. This requires Azure AD setup.

### Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────────┐    ┌─────────────┐
│ .twbx file  │───▶│ PBIP Output │───▶│ Power BI Service│───▶│ .pbix file  │
└─────────────┘    └─────────────┘    └─────────────────┘    └─────────────┘
     Step 1             Step 2              Step 3               Step 4
   (convert)         (generated)          (to-pbix)           (downloaded)
```

### Step 1: Create an Azure AD App Registration

1. Go to **[Azure Portal](https://portal.azure.com)**
2. Navigate to **Microsoft Entra ID** (formerly Azure Active Directory)
3. Click **App registrations** in the left menu
4. Click **+ New registration**
5. Configure the app:
   - **Name**: `Tableau-to-PowerBI-Converter` (or any name you prefer)
   - **Supported account types**: Select "Accounts in this organizational directory only"
   - **Redirect URI**: Leave blank (not needed for service principal)
6. Click **Register**

### Step 2: Get Your Client ID and Tenant ID

After registration, you'll see the **Overview** page:

- **Application (client) ID**: Copy this → This is your `AZURE_CLIENT_ID`
- **Directory (tenant) ID**: Copy this → This is your `AZURE_TENANT_ID`

### Step 3: Create a Client Secret

1. In your app registration, go to **Certificates & secrets**
2. Click **+ New client secret**
3. Enter a description (e.g., `powerbi-converter-secret`)
4. Choose an expiry (e.g., 24 months)
5. Click **Add**
6. **IMPORTANT**: Copy the **Value** immediately (it won't be shown again) → This is your `AZURE_CLIENT_SECRET`

### Step 4: Configure API Permissions

1. In your app registration, go to **API permissions**
2. Click **+ Add a permission**
3. Select **Power BI Service**
4. Select **Delegated permissions** and check:
   - `Workspace.ReadWrite.All`
   - `Report.ReadWrite.All`
   - `Dataset.ReadWrite.All`
5. Click **Add permissions**
6. Click **Grant admin consent for [Your Organization]** (requires admin rights)

### Step 5: Enable Service Principal Access in Power BI

This step requires **Power BI Admin** rights:

1. Go to **[Power BI Admin Portal](https://app.powerbi.com/admin-portal/tenantSettings)**
2. Navigate to **Tenant settings**
3. Scroll to **Developer settings**
4. Find **"Allow service principals to use Power BI APIs"**
5. Toggle it to **Enabled**
6. Choose either:
   - **The entire organization**, OR
   - **Specific security groups** (recommended - create a security group with your service principal)
7. Click **Apply**

> **Note**: Changes may take up to 15 minutes to propagate.

### Step 6: Create a Power BI Workspace

**Important**: "My Workspace" (personal workspace) cannot be accessed via service principal. You must create a dedicated workspace.

1. Go to **[Power BI Service](https://app.powerbi.com)**
2. Click **Workspaces** in the left sidebar
3. Click **+ Create a workspace** (or **+ New workspace**)
4. Enter a name (e.g., `Tableau Migration`)
5. Click **Save**
6. After creation, open the workspace and copy the **Workspace ID** from the URL:

```
https://app.powerbi.com/groups/████████-████-████-████-████████████/list
                              ↑
                    This GUID is your POWERBI_WORKSPACE_ID
```

### Step 7: Add Service Principal to the Workspace

1. Open your workspace in Power BI Service
2. Click **Manage access** (or **...** → **Manage access**)
3. Click **+ Add people or groups**
4. Search for your app registration name (e.g., `Tableau-to-PowerBI-Converter`)
5. Set role to **Admin** or **Member**
6. Click **Add**

### Step 8: Set Environment Variables

**macOS/Linux:**

```bash
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export POWERBI_WORKSPACE_ID="your-workspace-id"
```

**Windows (PowerShell):**

```powershell
$env:AZURE_TENANT_ID = "your-tenant-id"
$env:AZURE_CLIENT_ID = "your-client-id"
$env:AZURE_CLIENT_SECRET = "your-client-secret"
$env:POWERBI_WORKSPACE_ID = "your-workspace-id"
```

**Windows (Command Prompt):**

```cmd
set AZURE_TENANT_ID=your-tenant-id
set AZURE_CLIENT_ID=your-client-id
set AZURE_CLIENT_SECRET=your-client-secret
set POWERBI_WORKSPACE_ID=your-workspace-id
```

### Step 9: Convert PBIP to PBIX

```bash
# First, convert Tableau to PBIP
python main.py convert samples/sample_superstore.twbx -o output/

# Then, convert PBIP to PBIX via Power BI Service
python main.py to-pbix output/sample_superstore.pbip -o sample_superstore.pbix
```

### List Available Workspaces

To list all workspaces your service principal has access to:

```bash
python main.py workspaces
```

### Troubleshooting

| Error | Solution |
|-------|----------|
| `401 Unauthorized` | Check that your client secret is correct and not expired |
| `403 Forbidden` | Ensure service principal is added to the workspace with Admin/Member role |
| `Workspace not found` | Verify the workspace ID is correct (not "My Workspace") |
| `Service principal not enabled` | Enable service principal access in Power BI Admin Portal |
| `Insufficient permissions` | Grant admin consent for API permissions in Azure Portal |

### Security Best Practices

1. **Use specific security groups** instead of enabling service principals for the entire organization
2. **Rotate client secrets** regularly (set calendar reminders before expiry)
3. **Use least privilege** - only grant the permissions you need
4. **Store secrets securely** - use environment variables or a secret manager, never commit to git
5. **Monitor usage** - check Azure AD sign-in logs for unusual activity

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

## Sample Workbooks

The `samples/` directory contains example Tableau workbooks for testing and validating the converter:

### Basic Sample
- **`sample_superstore.twbx`** - The classic Superstore dataset with basic visualizations. Good for initial testing.

### Complex Samples (Advanced)

These complex samples test advanced Tableau features that require careful translation:

| Sample | Complexity | Description |
|--------|------------|-------------|
| **`complex_lod_expressions.twb`** | 🔴 HIGH | Tests all LOD expression types: `{FIXED}`, `{INCLUDE}`, `{EXCLUDE}`, nested LOD, and cohort analysis patterns. |
| **`table_calculations.twb`** | 🔴 VERY HIGH | Comprehensive table calculations: `RUNNING_*`, `WINDOW_*`, `RANK`, `LOOKUP`, `INDEX()`, `PREVIOUS_VALUE()`, and compound table calcs. |
| **`multi_source_joins.twb`** | 🔴 HIGH | Multiple data source types (SQL Server, PostgreSQL, Snowflake, BigQuery, Excel, CSV) with complex multi-table joins and cross-database references. |
| **`advanced_dashboard.twb`** | 🔴 HIGH | Complex dashboard layouts with KPI cards, filter actions, highlight actions, URL actions, parameter controls, and dynamic metrics. |
| **`nested_formulas.twb`** | 🔴 HIGH | Deep nested calculations: string parsing, date manipulation, fiscal calendars, conditional aggregations, risk scoring, and composite key generation. |

### What Each Sample Tests

#### complex_lod_expressions.twb
- `{FIXED : SUM([Sales])}` - Grand total LOD
- `{FIXED [Customer ID] : SUM([Sales])}` - Single dimension FIXED
- `{FIXED [Region], [Category] : SUM([Sales])}` - Multi-dimension FIXED
- `{INCLUDE [City] : AVG([Sales])}` - INCLUDE LOD
- `{EXCLUDE [State] : SUM([Sales])}` - EXCLUDE LOD
- Nested LOD: `{FIXED [Customer ID] : SUM([Sales])} / {FIXED : SUM([Sales])}`
- Cohort analysis patterns

#### table_calculations.twb
- `RUNNING_SUM()`, `RUNNING_AVG()`, `RUNNING_COUNT()`
- `WINDOW_SUM()`, `WINDOW_AVG()` with offsets
- `RANK()`, `RANK_DENSE()`, `RANK_PERCENTILE()`
- `INDEX()`, `FIRST()`, `LAST()`, `SIZE()`
- `LOOKUP()` for period comparisons
- `PREVIOUS_VALUE()` for recursive calculations
- Compound: `RUNNING_SUM() / TOTAL()`

#### multi_source_joins.twb
- SQL Server with 4-table joins (Orders, OrderDetails, Products, Customers)
- PostgreSQL with category hierarchies
- Excel budget data blending
- CSV exchange rates
- Snowflake web analytics
- BigQuery custom SQL with Customer 360 data
- Cross-source calculated fields

#### advanced_dashboard.twb
- 8 parameters (date range, metrics, targets, chart types)
- Dynamic date filtering with CASE expressions
- KPI cards with comparison metrics
- 10+ worksheets in dashboard layout
- Filter actions (select/hover triggers)
- Highlight actions across worksheets
- URL actions for drill-through
- Parameter-driven metrics and Top N filters

#### nested_formulas.twb
- String: `FIND()`, `LEFT()`, `RIGHT()`, `MID()`, `REPLACE()`, email/phone parsing
- Date: `DATEDIFF()`, `DATEADD()`, `DATETRUNC()`, `DATEPART()`, `DATENAME()`
- Fiscal calendar with parameterized start month
- Age/tenure calculations with bucket grouping
- `CASE WHEN` with 7+ conditions
- Composite key generation from multiple fields
- Risk scoring with multi-factor formula
- YTD/MTD/Prior Year comparisons

### Running Tests with Complex Samples

```bash
# Test LOD translations
python main.py convert samples/complex_lod_expressions.twb -o output/

# Test table calculations
python main.py convert samples/table_calculations.twb -o output/

# Full validation report
python main.py validate samples/nested_formulas.twb
```

## Limitations

- Table calculations with complex addressing may require manual review
- Some Tableau visuals have no direct Power BI equivalent
- Dashboard actions need manual configuration
- Row-level security requires manual setup
- Custom visuals (Gantt charts, etc.) may require marketplace alternatives

## License

MIT
