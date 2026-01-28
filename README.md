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

## Quick Start: Cloud Mode (No Windows Required!)

Convert Tableau to Power BI directly from Mac/Linux using the REST API:

```bash
# Set your Azure credentials
export AZURE_CLIENT_ID="c6688a3a-ce2f-46b7-8fe0-70add0f2530f"
export AZURE_TENANT_ID="0f50c60a-139b-4a49-b9a0-1c7e881236d6"
export AZURE_CLIENT_SECRET="your-client-secret-here"
export POWERBI_WORKSPACE_ID="your-workspace-id-here"

# Convert directly to Power BI Service
python3 main.py cloud samples/sample_superstore.twbx
```

This creates a dataset directly in Power BI Service - no Windows or PBIX file needed!

### Quick Setup

1. Edit `setup_powerbi.sh` with your credentials:
   ```bash
   # Add your client secret and workspace ID
   nano setup_powerbi.sh
   ```

2. Source and run:
   ```bash
   source setup_powerbi.sh
   python3 main.py cloud samples/sample_superstore.twbx
   ```

### Prerequisites for Cloud Mode

1. **Azure AD App** with Power BI API permissions
2. **Power BI Pro license** (free trial available)
3. **Service Principal** enabled in Power BI Admin Portal
4. **Workspace** with the service principal added as Admin/Member

See detailed setup below in "Converting to PBIX" section.

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

### Included Sample
- **`samples/sample_superstore.twbx`** - The classic Superstore dataset with basic visualizations. Good for initial testing.

```bash
# Convert the included sample
python main.py convert samples/sample_superstore.twbx -o output/
```

### Tableau Official Samples

For more comprehensive testing, download official Tableau sample workbooks:

| Sample | Download | What it Tests |
|--------|----------|---------------|
| **Superstore** | [Tableau Public](https://public.tableau.com/app/resources/sample-data) | Basic charts, filters, hierarchies |
| **World Indicators** | [Tableau Resources](https://public.tableau.com/app/resources/sample-data) | Maps, parameters, calculated fields |
| **Regional** | [Tableau Workbooks](https://public.tableau.com/app/resources/sample-data) | Multiple data sources, blending |

### Finding Test Workbooks

1. **Tableau Public Gallery**: Browse [public.tableau.com](https://public.tableau.com/app/discover) and download workbooks
2. **Your Own Workbooks**: Use your existing `.twbx` or `.twb` files
3. **Export from Tableau Server**: Download workbooks from your organization's Tableau Server

### Running Conversions

```bash
# Convert any Tableau workbook
python main.py convert path/to/your-workbook.twbx -o output/

# Generate a validation report
python main.py validate path/to/your-workbook.twbx

# Analyze a workbook before conversion
python main.py analyze path/to/your-workbook.twbx
```

### Supported Tableau Features

The converter handles these Tableau features:

| Feature | Support Level | Notes |
|---------|---------------|-------|
| Basic calculations | Full | SUM, AVG, COUNT, etc. |
| String functions | Full | LEFT, RIGHT, MID, FIND, etc. |
| Date functions | Full | DATEADD, DATEDIFF, DATETRUNC, etc. |
| LOD expressions | Partial | FIXED supported; INCLUDE/EXCLUDE require GenAI |
| Table calculations | Partial | RUNNING_*, WINDOW_* require GenAI |
| Parameters | Full | Converted to What-If parameters |
| Filters | Full | Converted to Power BI slicers |
| Charts/visuals | Full | Mapped to equivalent Power BI visuals |
| Dashboards | Partial | Layout preserved; actions require manual setup |

## Limitations

- Table calculations with complex addressing may require manual review
- Some Tableau visuals have no direct Power BI equivalent
- Dashboard actions need manual configuration
- Row-level security requires manual setup
- Custom visuals (Gantt charts, etc.) may require marketplace alternatives

## License

MIT
