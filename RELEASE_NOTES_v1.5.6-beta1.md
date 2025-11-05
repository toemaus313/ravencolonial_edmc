# v1.5.6-beta1 Release Notes

## ⚠️ Important: Manual Installation Required for v1.5.5 Users

**If you're running v1.5.5**, you must manually install this release. Auto-update from v1.5.5 has a bug that prevents automatic updating. After manually installing v1.5.6-beta1, auto-update will work for all future releases.

### Quick Manual Install (Linux/Mac):
```bash
cd ~/.local/share/EDMarketConnector/plugins/  # or ~/Library/Application Support/EDMarketConnector/plugins/ on Mac
rm -rf Ravencolonial-EDMC
unzip ~/Downloads/Ravencolonial-EDMC-v1.5.6-beta1.zip
```

### Quick Manual Install (Windows):
1. Navigate to `%LOCALAPPDATA%\EDMarketConnector\plugins\`
2. Delete the `Ravencolonial-EDMC` folder
3. Extract the ZIP and move the folder here
4. Restart EDMC

[Full installation instructions](https://github.com/toemaus313/ravencolonial_edmc/blob/main/MANUAL_UPDATE_INSTRUCTIONS.md)

---

## What's New

### Features
- **Body-Based Site Filtering**: Filter pre-planned sites by body in the Create Project dialog
- **Alphabetical Sort**: Optional alphabetical sorting for pre-planned sites
- **Auto-Trim Site Names**: Construction site prefixes are automatically removed when marking projects complete
- **Default Body Selection**: Body selector now defaults to "<None>" to show all sites

### Fixes
- ✅ **Linux Auto-Update**: Fixed cross-platform ZIP compatibility (will work after this manual update)
- ✅ **Version Display**: Fixed version number disappearing in settings
- ✅ **Settings UI**: Removed gray highlighting artifacts from help text
- ✅ **Pre-Release Version Handling**: Fixed version comparison for beta/alpha releases

### Developer Changes
- New Python-based release script for cross-platform compatibility
- Backward-compatible ZIP extraction code
- Improved error handling in auto-update process
- Added PATCH endpoint support for updating project names

---

## Full Changelog

### Added
- Body filtering dropdown in Create Project dialog with "<None>" default
- "Alphabetical Sort" checkbox for pre-planned sites list
- Auto-detection and removal of "Planetary/Orbital Construction Site: " prefixes on completion
- `update_project_name()` API method for PATCH requests
- Cross-platform Python release script (`make_release.py`)

### Fixed
- Version comparison now handles pre-release suffixes correctly (e.g., "1.5.6-beta1")
- Version number now displays consistently in settings page
- Gray background artifacts removed from settings help text
- Auto-update now works on Linux systems
- Backward-compatible ZIP extraction for smooth transitions

### Changed
- Settings help text now uses EDMC's native label widgets
- Removed warning emoji from auto-update caution text
- Improved logging in construction completion handler
- Better error messages in auto-update process

---

## Testing

This release has been tested on:
- ✅ Windows 10/11
- ✅ Linux (tested on Ubuntu-based systems)
- ⏳ macOS (community testing needed)

Please report any issues on [GitHub Issues](https://github.com/toemaus313/ravencolonial_edmc/issues).
