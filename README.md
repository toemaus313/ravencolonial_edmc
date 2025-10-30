# Ravencolonial EDMC Plugin

An Elite Dangerous Market Connector (EDMC) plugin that automatically tracks colonization activities and sends data to [Ravencolonial](https://ravencolonial.com), eliminating the need to run SRVSurvey continuously.

## Features

- **Automatic Tracking**: Monitors your colonization deliveries in real-time
- **Project Creation**: Create new colonization projects directly from EDMC (like SRVSurvey's "Colonize" button)
- **Seamless Integration**: Works with Ravencolonial's existing infrastructure
- **Lightweight**: Runs alongside EDMC with minimal resource usage
- **No Configuration Needed**: Works out of the box after installation
- **Smart UI**: Create Project button only enabled when docked at stations

## What This Plugin Does

This plugin provides the same colonization tracking functionality as SRVSurvey, but integrates directly with EDMC:

- **Create new colonization projects** with an easy-to-use dialog (replicates SRVSurvey's "Colonize" button)
- Tracks cargo deliveries to construction depots
- Automatically reports contributions to Ravencolonial
- Monitors your current projects
- Updates progress in real-time
- Auto-populates project details from journal data

## Installation

### Prerequisites

- [Elite Dangerous Market Connector (EDMC)](https://github.com/EDCD/EDMarketConnector/releases) version 5.0.0 or later
- Python 3.7+ (bundled with EDMC)

### Install Steps

1. **Download the Plugin**
   - Download the latest release from this repository
   - Or clone: `git clone https://github.com/[your-username]/Ravencolonial-EDMC.git`

2. **Install to EDMC**
   - Locate your EDMC plugins folder:
     - **Windows**: `%LOCALAPPDATA%\EDMarketConnector\plugins`
     - **Mac**: `~/Library/Application Support/EDMarketConnector/plugins`
     - **Linux**: `~/.local/share/EDMarketConnector/plugins`
   
   - Create a folder named `Ravencolonial` in the plugins directory
   - Copy `load.py` into the `Ravencolonial` folder

3. **Restart EDMC**
   - Close and restart EDMC
   - The plugin should appear in the EDMC UI and settings

## Usage

Once installed, the plugin works automatically:

1. **Start EDMC** before or while playing Elite Dangerous
2. **Dock at construction sites** and deliver cargo as usual
3. **Check your progress** on [ravencolonial.com](https://ravencolonial.com)

The plugin will display status updates in the EDMC main window showing:
- Current docking status
- Cargo delivery confirmations
- Connection status with Ravencolonial
- "🚧 Create Project" button (enabled when docked)

### Creating New Projects

When docked at a **Construction ship**, you can create a new colonization project:

1. **Dock at a Construction ship** at the colonization site
   - The "Create Project" button only enables at Construction ships
2. Click the **"🚧 Create Project"** button in the EDMC main window
3. Fill in the project details:
   - **Build Type**: Select from 28 types organized by tier:
     - Tier 3: Starports (Ocellus, Orbis, Coriolis, Asteroid Base)
     - Tier 1: Outposts (Civilian, Commercial, Industrial, Military, Scientific, Pirate)
     - Tier 2: Installations (Agricultural, Government, Industrial, Medical, Military, etc.)
     - Tier 1: Small Installations (Comms, Satellite)
     - Tier 1: Surface Settlements (Civilian, Industrial)
   - **Project Name**: Give your project a descriptive name (auto-suggested)
   - **Architect**: Your commander name (auto-filled)
   - **Pre-planned Site** (if available): Select an existing planned site or create new
   - **Primary Port**: Check if this is the system's main port
   - **Notes**: Any additional information about the project
   - **Discord Link**: Optional link to coordination Discord
4. Click **"Create"** to submit the project to Ravencolonial
5. The project page will automatically open in your browser

## How It Works

The plugin monitors Elite Dangerous journal files for these events:

- **Docked**: Tracks when you dock at construction sites
- **CargoDepot**: Detects cargo deliveries to construction depots
- **Market**: Monitors market interactions
- **Cargo**: Tracks your cargo hold contents
- **Location**: Updates your current system location

When you deliver cargo to a construction depot, the plugin:
1. Detects the delivery from the journal
2. Identifies the active colonization project
3. Sends the contribution data to Ravencolonial's API
4. Displays confirmation in EDMC

## API Integration

This plugin communicates with Ravencolonial's API:

- **Base URL**: `https://ravencolonial100-awcbdvabgze4c5cq.canadacentral-01.azurewebsites.net`
- **Endpoints Used**:
  - `GET /api/system/{systemAddress}/{marketId}` - Get project details
  - `POST /api/project/{buildId}/contribute/{cmdr}` - Submit cargo contributions
  - `GET /api/cmdr/{cmdr}` - Get commander's projects

All API calls are made asynchronously in a background thread to avoid blocking EDMC or the game.

## Troubleshooting

### Plugin Not Appearing in EDMC

- Ensure the plugin folder is named exactly `Ravencolonial`
- Verify `load.py` is in the correct location
- Check EDMC logs for errors: `%TEMP%\EDMarketConnector\EDMarketConnector.log`

### Deliveries Not Being Tracked

- Ensure you're connected to the internet
- Check that you're docked at a valid construction site
- Verify the project exists on ravencolonial.com
- Look for error messages in EDMC logs

### Status Shows "Not Connected"

- Check your internet connection
- Verify Ravencolonial API is online
- Restart EDMC to reset the connection

## Development

### Requirements

```
requests>=2.31.0
```

### Testing

To test the plugin during development:

1. Copy the plugin to your EDMC plugins folder
2. Enable EDMC debug logging
3. Monitor `EDMarketConnector.log` for plugin output
4. Use test journal events to simulate game activity

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Comparison with SRVSurvey

| Feature | SRVSurvey | This Plugin |
|---------|-----------|-------------|
| Colonization Tracking | ✅ | ✅ |
| Create Projects | ✅ | ✅ |
| EDMC Integration | ❌ | ✅ |
| Overlay UI | ✅ | ❌ |
| Bio Scanning | ✅ | ❌ |
| Guardian Sites | ✅ | ❌ |
| Always Running | ⚠️ Required | ❌ Optional |

**Use This Plugin If**:
- You already use EDMC for other purposes
- You only need colonization tracking
- You want a lightweight solution
- You don't need SRVSurvey's overlay features

**Use SRVSurvey If**:
- You need bio scanning or Guardian site features
- You want in-game overlay assistance
- You prefer a comprehensive exploration tool

## Credits

- **SRVSurvey**: Original colonization tracking implementation by [njthomson](https://github.com/njthomson/SrvSurvey)
- **Ravencolonial**: Colonization tracking platform also by njthomson
- **EDMC**: Elite Dangerous Market Connector by [EDCD](https://github.com/EDCD/EDMarketConnector)

## License

This plugin is licensed under the GNU General Public License v2.0 or later, consistent with EDMC's licensing.

## Support

- **Issues**: [GitHub Issues](https://github.com/[your-username]/Ravencolonial-EDMC/issues)
- **EDMC Wiki**: [Plugin Documentation](https://github.com/EDCD/EDMarketConnector/wiki/Plugins)
- **Ravencolonial**: [Website](https://ravencolonial.com)
- **SRVSurvey Discord**: [Guardian Science Corps](https://discord.gg/GJjTFa9fsz)

## Version History

### v1.1.0 (Current)
- **NEW**: Create Project dialog - replicate SRVSurvey's "Colonize" button functionality
- **NEW**: Smart button that enables only when docked
- Auto-populate project details from journal data
- Support for all build types (Installations and Outposts)
- Open created project in browser automatically

### v1.0.0 (Initial Release)
- Automatic colonization cargo delivery tracking
- Real-time reporting to Ravencolonial
- EDMC status display
- Background API calls
- Support for all construction depot deliveries
