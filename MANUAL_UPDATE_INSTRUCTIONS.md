# Manual Update Instructions for v1.5.5 Users

## Why Manual Update is Required

If you're running v1.5.5, the auto-update feature has a bug that prevents updating to v1.5.6-beta1. You need to manually install v1.5.6-beta1 **once**, and then auto-update will work for all future releases.

## Manual Installation Steps

### Windows

1. Download `Ravencolonial-EDMC-v1.5.6-beta1.zip` from the GitHub release
2. Close EDMarketConnector if it's running
3. Navigate to: `%LOCALAPPDATA%\EDMarketConnector\plugins\`
4. Delete the existing `Ravencolonial-EDMC` folder
5. Extract the ZIP file
6. Move the `Ravencolonial-EDMC` folder from the ZIP into the `plugins` folder
7. Restart EDMarketConnector

### Linux

1. Download `Ravencolonial-EDMC-v1.5.6-beta1.zip` from the GitHub release
2. Close EDMarketConnector if it's running
3. Navigate to: `~/.local/share/EDMarketConnector/plugins/`
4. Delete the existing `Ravencolonial-EDMC` folder:
   ```bash
   rm -rf ~/.local/share/EDMarketConnector/plugins/Ravencolonial-EDMC
   ```
5. Extract the ZIP file:
   ```bash
   cd ~/.local/share/EDMarketConnector/plugins/
   unzip ~/Downloads/Ravencolonial-EDMC-v1.5.6-beta1.zip
   ```
6. Restart EDMarketConnector

### macOS

1. Download `Ravencolonial-EDMC-v1.5.6-beta1.zip` from the GitHub release
2. Close EDMarketConnector if it's running
3. Navigate to: `~/Library/Application Support/EDMarketConnector/plugins/`
4. Delete the existing `Ravencolonial-EDMC` folder
5. Extract the ZIP file
6. Move the `Ravencolonial-EDMC` folder from the ZIP into the `plugins` folder
7. Restart EDMarketConnector

## After Manual Update

Once you've manually installed v1.5.6-beta1, the auto-update feature will work normally for all future updates. You won't need to do this again.

## Verifying Installation

After restarting EDMarketConnector:
1. Go to File → Settings → Ravencolonial-EDMC
2. Check that the version shows "1.5.6-beta1" at the bottom
3. Auto-update will work for future releases

## What's Fixed in v1.5.6-beta1

- ✅ Auto-update now works on Linux
- ✅ Cross-platform ZIP compatibility
- ✅ Fixed construction site prefix stripping on completion
- ✅ Body-based filtering for pre-planned sites
- ✅ Alphabetical sort option for pre-planned sites
- ✅ Various UI improvements
