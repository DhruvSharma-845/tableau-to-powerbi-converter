#!/usr/bin/env python3
"""
Convert PBIP to PBIX using Power BI Desktop.

This script automates the conversion from PBIP (Power BI Project) format
to PBIX (Power BI Desktop file) format.

Requirements:
- Power BI Desktop installed
- Windows OS (Power BI Desktop is Windows-only)

For macOS/Linux users:
- Use a Windows VM or
- Use Power BI Service to import and export
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import platform


def find_powerbi_desktop() -> str:
    """Find Power BI Desktop installation path."""
    if platform.system() != "Windows":
        return None
    
    # Common installation paths
    possible_paths = [
        r"C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe",
        r"C:\Program Files (x86)\Microsoft Power BI Desktop\bin\PBIDesktop.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Power BI Desktop\bin\PBIDesktop.exe"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def convert_pbip_to_pbix_windows(pbip_path: str, output_path: str) -> bool:
    """
    Convert PBIP to PBIX on Windows using Power BI Desktop.
    
    Note: This is a semi-automated approach. Power BI Desktop doesn't have
    a direct command-line conversion, so this opens the file and you
    need to save manually.
    """
    pbi_exe = find_powerbi_desktop()
    
    if not pbi_exe:
        print("Power BI Desktop not found. Please install it first.")
        print("Download: https://powerbi.microsoft.com/desktop/")
        return False
    
    pbip_file = Path(pbip_path)
    if not pbip_file.exists():
        print(f"PBIP file not found: {pbip_path}")
        return False
    
    # Find the .pbip file inside the directory
    if pbip_file.is_dir():
        pbip_files = list(pbip_file.glob("*.pbip"))
        if pbip_files:
            pbip_file = pbip_files[0]
        else:
            print(f"No .pbip file found in {pbip_path}")
            return False
    
    print(f"Opening {pbip_file} in Power BI Desktop...")
    print("\nManual steps required:")
    print("1. Wait for Power BI Desktop to load the file")
    print("2. Click File → Save As")
    print(f"3. Save as: {output_path}")
    print("4. Select 'Power BI Desktop (*.pbix)' as file type")
    
    # Open Power BI Desktop with the file
    subprocess.Popen([pbi_exe, str(pbip_file)])
    
    return True


def create_conversion_instructions(pbip_path: str) -> str:
    """Create instructions for manual conversion."""
    return f"""
================================================================================
                    PBIP to PBIX Conversion Instructions
================================================================================

Your Power BI Project has been created at:
  {pbip_path}

To convert to PBIX format, follow these steps:

FOR WINDOWS USERS:
------------------
1. Install Power BI Desktop (if not already installed)
   Download: https://powerbi.microsoft.com/desktop/

2. Enable Developer Mode in Power BI Desktop:
   - Open Power BI Desktop
   - Go to File → Options and Settings → Options
   - Select "Preview features"
   - Check "Power BI Project (.pbip) save option"
   - Click OK and restart Power BI Desktop

3. Open the PBIP file:
   - File → Open report
   - Navigate to: {pbip_path}
   - Open the .pbip file

4. Save as PBIX:
   - File → Save as
   - Choose "Power BI Desktop (*.pbix)" as file type
   - Save

FOR MAC/LINUX USERS:
--------------------
Option A: Use a Windows VM
  - Install Windows in a virtual machine (Parallels, VMware, VirtualBox)
  - Install Power BI Desktop in the VM
  - Follow Windows instructions above

Option B: Use Power BI Service (Cloud)
  1. Go to https://app.powerbi.com
  2. Create a new workspace (or use existing)
  3. Upload the PBIP folder contents manually:
     - Create a new report
     - Import the data model
     - Recreate visuals based on the JSON definitions
  4. Download as PBIX from the service

Option C: Use pbi-tools (Third-party)
  - Install: https://pbi.tools
  - Command: pbi-tools compile "{pbip_path}" -outPath output.pbix
  (Note: pbi-tools requires .NET and Windows)

================================================================================
"""


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python convert_to_pbix.py <pbip_path> [output.pbix]")
        sys.exit(1)
    
    pbip_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else pbip_path.replace(".pbip", ".pbix")
    
    if platform.system() == "Windows":
        success = convert_pbip_to_pbix_windows(pbip_path, output_path)
        if not success:
            print(create_conversion_instructions(pbip_path))
    else:
        print(create_conversion_instructions(pbip_path))


if __name__ == "__main__":
    main()
