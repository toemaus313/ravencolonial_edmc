# Auto-Update Feature

## Overview

Your plugin now includes a complete auto-update system adapted from the `edmc-raven-colonial` plugin. This feature allows your plugin to automatically check for and install updates from GitHub.

## What Was Added

### New Files
1. **`version_check.py`** - Core auto-update module
   - Checks GitHub API for latest release
   - Downloads and installs updates
   - Handles backup/rollback on failure
   - Simple semantic version comparison (no external dependencies)

### Modified Files
1. **`requirements.txt`** - No changes (uses only `requests` which EDMC already includes)
2. **`plugin_config/settings.py`** - Added update configuration methods
3. **`load.py`** - Integrated update checking on startup
4. **`ui/manager.py`** - Added update notification banner with action buttons
5. **`make_release.ps1`** - Updated to include new files in releases

## Features

### Three Configuration Options (in Settings)
1. **Check for updates on startup** (default: ON)
   - Checks GitHub for new releases when EDMC starts
   
2. **Automatically install updates** (default: OFF)
   - Silently downloads and installs updates
   - Requires EDMC restart to activate
   
3. **Include pre-release versions** (default: OFF)
   - Checks for beta/rc releases in addition to stable

### Update Notification UI
When an update is available (and auto-update is OFF), users see a banner with:
- Current version → New version display
- **📥 Go to Download** - Opens GitHub release page
- **⚡ Auto-Update** - Manually triggers auto-install
- **✖ Dismiss** - Hides the notification

### Safety Features
- ✅ **Dev build protection** - Won't update dev/0.0.0 versions
- ✅ **Automatic backup** - Creates backup before updating
- ✅ **Rollback on failure** - Restores backup if update fails
- ✅ **Background threads** - Non-blocking, won't freeze EDMC
- ✅ **User confirmation** - Auto-update defaults to OFF

## How It Works

### On Plugin Startup
1. If "Check for updates" is enabled:
   - Spawns background thread after 2-second delay
   - Queries GitHub API: `https://api.github.com/repos/toemaus313/ravencolonial_edmc/releases/latest`
   - Compares versions using simple semantic versioning

2. If update is available:
   - **Auto-update ON**: Silently installs, shows "Restart EDMC" message
   - **Auto-update OFF**: Shows notification banner in UI

### Update Process
When auto-update is triggered (automatically or manually):
1. Downloads ZIP from GitHub release assets
2. Extracts to temporary directory
3. Moves current plugin to backup folder (random name + `.disabled`)
4. Moves new version to plugin folder
5. Deletes backup on success
6. Shows "Restart EDMC" notification

### If Update Fails
1. Logs detailed error
2. Removes partially installed files
3. Restores backup folder
4. Shows error notification
5. Plugin continues working with old version

## GitHub Release Requirements

For auto-update to work, your GitHub releases must:
1. Have a version tag (e.g., `v1.5.4`, `1.5.4`)
2. Include a ZIP asset named: `Ravencolonial-EDMC-v{version}.zip`
3. ZIP must contain a single folder: `Ravencolonial-EDMC/` with all plugin files

Your existing `make_release.ps1` script already creates properly formatted ZIPs.

## Testing Recommendations

### Before First Release with Auto-Update

1. **Test update checking**
   ```powershell
   # Temporarily change VERSION in plugin_config/settings.py to something old
   VERSION = "1.0.0"
   # Restart EDMC, should detect update available
   ```

2. **Test manual auto-update**
   - Enable "Check for updates" in settings
   - Disable "Automatically install updates"
   - Wait for notification banner
   - Click "⚡ Auto-Update" button
   - Verify backup/install/rollback

3. **Test automatic auto-update**
   - Enable both checkboxes
   - Restart EDMC
   - Should silently install update

4. **Test failure handling**
   - Temporarily break the update (e.g., corrupt ZIP URL)
   - Verify rollback works
   - Plugin still functions

### Version String Format

Always use semantic versioning in `load.py` and `plugin_config/settings.py`:
```python
plugin_version = "1.5.3"  # Good: major.minor.patch
VERSION = "1.5.3"         # Good: matches load.py

# Avoid:
plugin_version = "v1.5.3"  # Bad: prefix confuses parser
plugin_version = "dev"     # Bad: not comparable (but protected)
```

## User Instructions

### For Plugin Users

1. **Enable Update Checking** (Recommended)
   - Open EDMC Settings → Ravencolonial-EDMC tab
   - Check "Check for updates on startup"
   - Click "Save Settings"

2. **Optional: Enable Auto-Update**
   - Check "Automatically install updates"
   - Updates will install silently on startup
   - You'll see "Restart EDMC" message when ready

3. **When Update Notification Appears**
   - **Go to Download**: Manual download from GitHub
   - **Auto-Update**: One-click install (requires EDMC restart)
   - **Dismiss**: Hide notification (won't show again this session)

## Developer Notes

### Version Comparison
Uses simple built-in version comparison (no external dependencies):
```python
def compare_versions(current: str, latest: str) -> bool:
    # Remove 'v' prefix if present
    current = current.lstrip('v')
    latest = latest.lstrip('v')
    
    # Parse to tuples: "1.5.3" -> (1, 5, 3)
    current_parts = tuple(int(x) for x in current.split('.'))
    latest_parts = tuple(int(x) for x in latest.split('.'))
    
    # Python compares tuples element by element
    return latest_parts > current_parts

# Example:
compare_versions("1.5.3", "v1.6.0")  # True
compare_versions("1.5.3", "1.5.2")   # False
```

**Supported formats**: `1.5.3`, `v1.5.3`, `1.5.3-beta` (ignores suffix)
**Note**: Pre-release suffixes (e.g., `-beta`, `-rc1`) are ignored by the simple parser.

### GitHub API Response
```json
{
  "tag_name": "v1.5.4",
  "html_url": "https://github.com/toemaus313/ravencolonial_edmc/releases/tag/v1.5.4",
  "assets": [
    {
      "name": "Ravencolonial-EDMC-v1.5.4.zip",
      "browser_download_url": "https://github.com/.../Ravencolonial-EDMC-v1.5.4.zip"
    }
  ]
}
```

### File Operations
```python
# Current plugin location
live_dir = os.path.dirname(os.path.abspath(__file__))
# Example: C:\Users\...\EDMarketConnector\plugins\Ravencolonial-EDMC

# Backup location (random name to avoid conflicts)
backup_dir = os.path.join(live_dir, "..", "abc123def456.backup.disabled")
# Example: C:\Users\...\EDMarketConnector\plugins\abc123def456.backup.disabled

# .disabled suffix prevents EDMC from loading the old version
```

## Troubleshooting

### Update Check Fails
- Check internet connection
- Verify GitHub API is accessible
- Check EDMC logs for detailed error

### Auto-Update Fails
- Check file permissions on plugins folder
- Ensure no other EDMC instances running
- Check if antivirus is blocking file operations
- Review EDMC logs for specific error

### Version Shows as "unknown"
- Verify `VERSION` in `plugin_config/settings.py` matches `plugin_version` in `load.py`
- Check for typos in version string

## Credits

Auto-update implementation adapted from:
- **EDMC-RavenColonial** by CMDR-WDX
- Original version_check.py: https://github.com/CMDR-WDX/edmc-raven-colonial

## Future Enhancements

Possible improvements:
- [ ] Update history/changelog display
- [ ] Scheduled update checks (not just on startup)
- [ ] Notification sound/toast
- [ ] Update size display before download
- [ ] Bandwidth-friendly update checks (ETag/If-Modified-Since)
