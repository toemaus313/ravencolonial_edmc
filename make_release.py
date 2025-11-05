#!/usr/bin/env python3
"""
Cross-platform Release Package Script for Ravencolonial-EDMC
Creates a distributable .zip file with correct versioning

ZIP Structure:
    Ravencolonial-EDMC-vX.Y.Z.zip
    └── Ravencolonial-EDMC/
        ├── load.py
        ├── api/
        ├── config/
        └── ... (all plugin files)

This subdirectory structure is the STANDARD format and should be maintained
for all future releases. The auto-update code is designed to handle this structure.
"""

import os
import re
import shutil
import zipfile
from pathlib import Path

def get_version():
    """Extract version from load.py"""
    load_py = Path("load.py")
    if not load_py.exists():
        raise FileNotFoundError("load.py not found")
    
    content = load_py.read_text()
    match = re.search(r'plugin_version\s*=\s*"([^"]+)"', content)
    if not match:
        raise ValueError("Could not find plugin_version in load.py")
    
    return match.group(1)

def main():
    print("=== Ravencolonial-EDMC Release Packager ===\n")
    
    # Get version
    version = get_version()
    print(f"Found version: {version}")
    
    # Define paths
    plugin_folder_name = "Ravencolonial-EDMC"
    zip_filename = f"{plugin_folder_name}-v{version}.zip"
    
    # Files to include
    files_to_include = [
        "load.py",
        "README.md",
        "requirements.txt",
        "construction_completion.py",
        "create_project_dialog.py",
        "fleet_carrier_handler.py",
        "version_check.py",
    ]
    
    # Directories to include
    dirs_to_include = [
        "api",
        "config",
        "handlers",
        "L10n",
        "models",
        "ui",
        "plugin_config"
    ]
    
    print(f"\nPackage details:")
    print(f"  Plugin folder: {plugin_folder_name}")
    print(f"  Version: {version}")
    print(f"  Output file: {zip_filename}\n")
    
    # Remove old zip if exists
    if Path(zip_filename).exists():
        print(f"WARNING: {zip_filename} already exists - overwriting")
        os.remove(zip_filename)
    
    # Create zip with subdirectory structure
    print("Creating zip archive...\n")
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add individual files
        print("Adding files:")
        for file in files_to_include:
            if Path(file).exists():
                arcname = f"{plugin_folder_name}/{file}"
                zipf.write(file, arcname)
                print(f"  + {file}")
            else:
                print(f"  ! {file} not found (skipping)")
        
        # Add directories recursively
        print("\nAdding directories:")
        for dir_name in dirs_to_include:
            dir_path = Path(dir_name)
            if dir_path.exists():
                file_count = 0
                for root, dirs, files in os.walk(dir_path):
                    # Skip __pycache__ directories
                    if '__pycache__' in root:
                        continue
                    
                    for file in files:
                        # Skip .pyc files
                        if file.endswith('.pyc'):
                            continue
                        
                        file_path = Path(root) / file
                        arcname = f"{plugin_folder_name}/{file_path}"
                        zipf.write(file_path, arcname)
                        file_count += 1
                
                print(f"  + {dir_name} ({file_count} files)")
            else:
                print(f"  ! {dir_name} not found (skipping)")
    
    # Get file size
    zip_size = Path(zip_filename).stat().st_size
    zip_size_kb = round(zip_size / 1024, 2)
    
    print(f"\nSUCCESS: Release package created!")
    print(f"  File: {zip_filename}")
    print(f"  Size: {zip_size_kb} KB")
    print(f"\nNext steps:")
    print(f"  1. Test the plugin by extracting to EDMC plugins folder")
    print(f"  2. Create a GitHub release with tag v{version}")
    print(f"  3. Upload {zip_filename} to the release")

if __name__ == "__main__":
    main()
