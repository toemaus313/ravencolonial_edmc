# Changelog

All notable changes to the Ravencolonial EDMC Plugin will be documented in this file.

## [1.2.0] - 2025-10-29

### Added
- **Construction Ship Detection**: Create Project button now only enables when docked at a Construction ship (matches SRVSurvey behavior)
- **Pre-planned Site Selection**: If system has pre-planned sites, dropdown allows selecting existing sites
- **Complete Build Type List**: Added all 28 build types organized by tier (Starports, Outposts, Installations, Settlements)
- Better button states: Shows "Need Construction Ship" or "Dock First" messages

### Changed
- Reorganized Build Type menu to match SRVSurvey's structure and grouping
- Window size increased to 550x650 to accommodate new features
- Removed Faction field (not used by API)

### Fixed
- URL format now uses `#build=` hash format: `https://ravencolonial.com/#build={buildId}`

## [1.1.0] - 2025-10-29

### Added
- **Create Project Dialog**: Full-featured dialog for creating new colonization projects
  - Replicates SRVSurvey's "Colonize" button functionality
  - Support for all build types (Agricultural, Extraction, Industrial, Military, Scientific, Tourist Installations + Civilian, Commercial, Industrial, Military Outposts)
  - Auto-populates project name, architect, system, station details from journal
  - Optional fields: Notes, Discord link, Faction name, Primary Port flag
- **Smart "Create Project" button** in main EDMC window
  - Only enabled when docked at a station
  - Shows "🚧 Create Project" when available
  - Shows "Create Project (Dock First)" when disabled
- Enhanced journal tracking for additional fields:
  - StarPos (star coordinates)
  - BodyID and Body name
  - StationType
  - StationFaction
  - Docked/Undocked state tracking
- Auto-open created project in browser after successful creation
- Better error handling with user-friendly error messages

### Changed
- Updated version to 1.1.0
- Enhanced UI with side-by-side status label and button
- Improved status messages for docking/undocking events

### Technical
- Added `CreateProjectDialog` class with full project creation UI
- New API methods: `get_system_sites()`, `create_project()`
- Added `urllib.parse` for proper URL encoding
- Enhanced state tracking in `RavencolonialPlugin` class

## [1.0.0] - 2025-10-29

### Added
- Initial release
- Automatic tracking of colonization cargo deliveries
- Real-time reporting to Ravencolonial API
- Background thread for non-blocking API calls
- Status display in EDMC main window
- Settings panel with plugin information
- Support for CargoDepot journal events
- Commander and location tracking
- Project identification by system address and market ID

### Features
- Monitors `Docked`, `Location`, `CargoDepot`, `Market`, and `Cargo` journal events
- Asynchronous API communication with Ravencolonial backend
- Automatic cargo contribution submission
- Thread-safe API queue management
- Graceful error handling and logging

### API Integration
- GET `/api/system/{systemAddress}/{marketId}` - Fetch project details
- POST `/api/project/{buildId}/contribute/{cmdr}` - Submit contributions
- GET `/api/cmdr/{cmdr}` - Fetch commander's projects

### Technical Details
- Compatible with EDMC 5.0.0+
- Python 3.7+ support
- Async API calls via worker thread
- Proper plugin lifecycle management (start/stop)
- Comprehensive logging for debugging
