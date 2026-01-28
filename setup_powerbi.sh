#!/bin/bash
# Power BI REST API Configuration
# Source this file to set environment variables:
#   source setup_powerbi.sh
#
# Then run:
#   python3 main.py cloud samples/sample_superstore.twbx

# Azure AD App Registration
export AZURE_CLIENT_ID="c6688a3a-ce2f-46b7-8fe0-70add0f2530f"
export AZURE_TENANT_ID="0f50c60a-139b-4a49-b9a0-1c7e881236d6"

# Client Secret (create in Azure Portal -> App registrations -> Certificates & secrets)
# IMPORTANT: Replace with your actual secret!
export AZURE_CLIENT_SECRET="YOUR_CLIENT_SECRET_HERE"

# Power BI Workspace ID (get from workspace URL in app.powerbi.com)
# URL format: https://app.powerbi.com/groups/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX/...
export POWERBI_WORKSPACE_ID="YOUR_WORKSPACE_ID_HERE"

echo "Power BI environment variables set!"
echo "  AZURE_CLIENT_ID: $AZURE_CLIENT_ID"
echo "  AZURE_TENANT_ID: $AZURE_TENANT_ID"
echo "  AZURE_CLIENT_SECRET: ${AZURE_CLIENT_SECRET:0:10}..."
echo "  POWERBI_WORKSPACE_ID: $POWERBI_WORKSPACE_ID"
echo ""
echo "Run: python3 main.py cloud samples/sample_superstore.twbx"
