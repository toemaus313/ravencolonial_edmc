# Ravencolonial EDMC Plugin

An Elite Dangerous Market Connector (EDMC) plugin that automatically tracks colonization activities and sends data to [Ravencolonial](https://ravencolonial.com), eliminating the need to run SRVSurvey continuously.

## Features

- **Automatic Tracking**: Monitors your colonization deliveries in real-time
- **Project Creation**: Create new colonization projects directly from EDMC (like SRVSurvey's "Colonize" button)
- **Seamless Integration**: Works with Ravencolonial's existing infrastructure
- **Lightweight**: Runs alongside EDMC with minimal resource usage
- **No Configuration Needed**: Works out of the box after installation
- **Smart UI**: Create Project button only enabled when docked at stations
- **Fleet Carrier Support**: Automatically tracks and updates commodity quantities on linked Fleet Carriers
  - **__FLEET CARRIER SUPPORT REQUIRES YOU TO ENTER YOUR RAVENCOLONIAL API KEY IN SETTINGS->RAVENCOLONIAL-EDMC__**
- **Stealth Mode**: Optional privacy feature that stops sending Fleet Carrier commodity data to Ravencolonial

## What This Plugin Does

This plugin provides the same colonization tracking functionality as SRVSurvey, but integrates directly with EDMC:

- **Create new colonization projects** with an easy-to-use dialog (replicates SRVSurvey's "Colonize" button)
- Tracks cargo deliveries to construction depots
- Automatically reports contributions to Ravencolonial
- Monitors your current projects
- Updates progress in real-time
- Auto-populates project details from journal data
- **Fleet Carrier commodity tracking**: Monitors buy/sell operations and cargo transfers on linked Fleet Carriers
- **Real-time FC updates**: Automatically updates Ravencolonial when your Fleet Carrier's commodity levels change

## Configuration

The Ravencolonial plugin includes a settings page in EDMC where you can configure:

### API Key
- **Required for Fleet Carrier tracking**: Get your API key from your Ravencolonial account settings
- The API key is used to authenticate Fleet Carrier commodity updates
- Find this in the upper-right corner of your Ravencolonial dashboard in your user settings
- **Optional for basic colonization tracking**: The plugin works for colonization project tracking without an API key
- Stored securely in EDMC's configuration

### Stealth Mode
- **Optional privacy feature**: When enabled, stops sending Fleet Carrier commodity data to Ravencolonial
- Useful if you want to use the plugin for colonization tracking but keep your FC cargo private
- Only affects Fleet Carrier commodity tracking - colonization project tracking continues normally

### Accessing Settings
1. Open EDMC
2. Go to **Settings** (click the gear icon)
3. Select the **Ravencolonial** tab
4. Configure your API key and Stealth Mode preference
5. Click **Save Settings**

### Prerequisites

- [Elite Dangerous Market Connector (EDMC)](https://github.com/EDCD/EDMarketConnector/releases) version 5.0.0 or later
- Python 3.7+ (bundled with EDMC)
- Ravencolonial account (for API key and project tracking)

### Install Steps

1. **Download the Plugin**
   - Download the latest release from this repository

2. **Install to EDMC**
   - Locate your EDMC plugins folder:
     - **Windows**: `%LOCALAPPDATA%\EDMarketConnector\plugins`
     - **Linux**: `~/.local/share/EDMarketConnector/plugins`
   
   - Unzip the Ravencolonial-EDMC folder to the plugins folder

3. **Restart EDMC**
   - Close and restart EDMC
   - The plugin should appear in the EDMC UI and settings

4. **Configure the Plugin**
   - Go to **Settings** (click the gear icon)
   - Select the **Ravencolonial** tab
   - Configure your API key and Stealth Mode preference (optional)
   - Configure auto-update preferences
   - Click **Save Settings**

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

## Credits

- **SRVSurvey**: Original colonization tracking implementation by [grinning2001](https://github.com/njthomson/SrvSurvey)
- **Ravencolonial**: Colonization tracking platform also by [grinning2001](https://ravencolonial.com)
- **EDMC**: Elite Dangerous Market Connector by [EDCD](https://github.com/EDCD/EDMarketConnector)
- **This half-assed plugin**: Me, [toemaus313 aka CMDR Dirk Pitt13](https://github.com/toemaus313/Ravencolonial-EDMC)

## License

This plugin is licensed under the GNU General Public License v2.0 or later, consistent with EDMC's licensing.

## Support

- **Issues**: [GitHub Issues](https://github.com/[your-username]/Ravencolonial-EDMC/issues)
- **Discord**: @toemaus313
- **EDMC Wiki**: [Plugin Documentation](https://github.com/EDCD/EDMarketConnector/wiki/Plugins)
- **Ravencolonial**: [Website](https://ravencolonial.com)
- **SRVSurvey Discord**: [Guardian Science Corps](https://discord.gg/GJjTFa9fsz)

## Version History

### v1.5.6 (2025-11-05)
- Improved compatibility for auto-updates
- Improvements to filtering in Create Project dialog
- 

### v1.5.1 (2025-11-01)
- Added support for Fleet Carrier
- Added Fleet Carrier stealth mode
- Added settings page for API key and stealth mode

### v1.4.1 (2025-11-01)
- Bugfix for system bodies sometimes not displaying properly

### v1.4.0 (2025-10-31)
- Initial release

