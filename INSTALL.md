# Installation Guide

## Quick Install

1. **Locate your EDMC plugins folder:**
   - **Windows**: `%LOCALAPPDATA%\EDMarketConnector\plugins`
   - **Mac**: `~/Library/Application Support/EDMarketConnector/plugins`
   - **Linux**: `~/.local/share/EDMarketConnector/plugins`

2. **Create plugin folder:**
   ```
   mkdir Ravencolonial
   ```

3. **Copy files:**
   - Copy `load.py` into the `Ravencolonial` folder

4. **Restart EDMC**

## Verify Installation

After restarting EDMC, you should see:
- "Ravencolonial" listed in File > Settings > Plugins tab
- "Ravencolonial: Ready" status in the main EDMC window

## Dependencies

The plugin requires the `requests` library, which is typically included with EDMC. If you encounter import errors, install it:

```bash
pip install requests
```

## Testing

To verify the plugin is working:

1. Start Elite Dangerous and EDMC
2. Dock at any construction site with an active colonization project
3. Deliver cargo to the construction depot
4. Check the EDMC window for delivery confirmation
5. Verify on ravencolonial.com that your contribution was recorded

## Troubleshooting

**Plugin doesn't appear:**
- Ensure folder is named exactly `Ravencolonial` (case-sensitive on Linux/Mac)
- Check that `load.py` is directly in the `Ravencolonial` folder, not in a subfolder
- Restart EDMC completely (not just reload)

**Import errors:**
- Update EDMC to the latest version
- Install requests: `pip install requests>=2.31.0`

**No deliveries tracked:**
- Ensure you're docked at a construction site
- Check that the project exists on ravencolonial.com
- Look for errors in EDMC log: `%TEMP%\EDMarketConnector\EDMarketConnector.log`
