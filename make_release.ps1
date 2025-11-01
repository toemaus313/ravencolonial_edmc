#!/usr/bin/env pwsh
# Release Package Script for Ravencolonial-EDMC
# Creates a distributable .zip file with correct versioning

param(
    [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"

# Color output functions
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Failure { Write-Host $args -ForegroundColor Red }

Write-Info "=== Ravencolonial-EDMC Release Packager ==="
Write-Info ""

# Extract version from load.py
$loadPyPath = "load.py"
if (-not (Test-Path $loadPyPath)) {
    Write-Failure "ERROR: load.py not found in current directory"
    exit 1
}

# Find version line by reading file
$version = $null
foreach ($line in Get-Content $loadPyPath) {
    if ($line -match '^\s*plugin_version\s*=\s*"([^"]+)"\s*$') {
        $version = $matches[1]
        break
    }
}

if (-not $version) {
    Write-Failure "ERROR: Could not find plugin_version in load.py"
    exit 1
}
Write-Success "Found version: $version"

# Define output names
$pluginFolderName = "Ravencolonial-EDMC"
$zipFileName = "$pluginFolderName-v$version.zip"
$tempDir = "temp_release"

# Files to include
$filesToInclude = @(
    "load.py",
    "README.md",
    "plugin_config.py",
    "construction_completion.py",
    "create_project_dialog.py",
    "fleet_carrier_handler.py",
    "L10n\en.template"
)

# Directories to include (recursively)
$dirsToInclude = @(
    "api",
    "handlers",
    "models",
    "ui"
)

Write-Info ""
Write-Info "Package details:"
Write-Info "  Plugin folder: $pluginFolderName"
Write-Info "  Version: $version"
Write-Info "  Output file: $zipFileName"
Write-Info ""

if ($DryRun) {
    Write-Warning "DRY RUN MODE - No files will be created"
    Write-Info ""
}

# Check if output file already exists
if (Test-Path $zipFileName) {
    Write-Warning "WARNING: $zipFileName already exists - overwriting"
    if (-not $DryRun) {
        Remove-Item $zipFileName -Force
    }
}

if (-not $DryRun) {
    # Create temp directory structure
    Write-Info "Creating temporary directory structure..."
    $targetDir = Join-Path $tempDir $pluginFolderName
    if (Test-Path $tempDir) {
        Remove-Item $tempDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null

    # Copy individual files
    Write-Info "Copying files..."
    foreach ($file in $filesToInclude) {
        if (Test-Path $file) {
            $targetPath = Join-Path $targetDir $file
            $targetParent = Split-Path $targetPath -Parent
            if (-not (Test-Path $targetParent)) {
                New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
            }
            Copy-Item $file -Destination $targetPath
            Write-Info "  + $file"
        } else {
            Write-Warning "  ! $file not found (skipping)"
        }
    }

    # Copy directories recursively
    Write-Info "Copying directories..."
    foreach ($dir in $dirsToInclude) {
        if (Test-Path $dir) {
            $targetPath = Join-Path $targetDir $dir
            Copy-Item $dir -Destination $targetPath -Recurse -Force
            
            # Clean up __pycache__ and .pyc files
            Get-ChildItem -Path $targetPath -Include "__pycache__" -Recurse -Force | Remove-Item -Recurse -Force
            Get-ChildItem -Path $targetPath -Filter "*.pyc" -Recurse -Force | Remove-Item -Force
            
            $fileCount = (Get-ChildItem -Path $targetPath -Recurse -File).Count
            Write-Info ("  + {0} ({1} files)" -f $dir, $fileCount)
        } else {
            Write-Warning ("  ! {0} not found (skipping)" -f $dir)
        }
    }

    # Create zip file
    Write-Info ""
    Write-Info "Creating zip archive..."
    Compress-Archive -Path (Join-Path $tempDir "*") -DestinationPath $zipFileName -Force
    
    # Clean up temp directory
    Remove-Item $tempDir -Recurse -Force

    # Get file size
    $zipSize = (Get-Item $zipFileName).Length
    $zipSizeKB = [math]::Round($zipSize / 1KB, 2)
    
    Write-Success ""
    Write-Success "SUCCESS: Release package created!"
    Write-Success "  File: $zipFileName"
    Write-Success "  Size: $zipSizeKB KB"
    Write-Info ""
    Write-Info "Next steps:"
    Write-Info "  1. Test the plugin by extracting to EDMC plugins folder"
    Write-Info "  2. Create a GitHub release with tag v$version"
    Write-Info "  3. Upload $zipFileName to the release"
} else {
    Write-Info "Files that would be included:"
    foreach ($file in $filesToInclude) {
        if (Test-Path $file) {
            Write-Info "  + $file"
        } else {
            Write-Warning "  - $file (not found)"
        }
    }
    foreach ($dir in $dirsToInclude) {
        if (Test-Path $dir) {
            $fileCount = (Get-ChildItem -Path $dir -Recurse -File).Count
            Write-Info ("  + {0}\ ({1} files)" -f $dir, $fileCount)
        } else {
            Write-Warning ("  - {0}\ (not found)" -f $dir)
        }
    }
    
    Write-Info ""
    Write-Info "Would create: $zipFileName"
    Write-Info ""
    Write-Info "Run without -DryRun to create the package"
}
