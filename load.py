"""
EDMC Plugin for Ravencolonial Colonization Tracking

This plugin tracks Elite Dangerous colonization activities and sends data
to Ravencolonial (ravencolonial.com) by grinning2001
"""

import tkinter as tk
from tkinter import ttk, messagebox
import myNotebook as nb
from config import appname, config
from companion import CAPIData
from typing import Optional, Dict, Any, List
from threading import Thread
import queue
import logging
import os
import functools
import l10n
import plug
import create_project_dialog
import webbrowser

# Import new modular components
from api import RavencolonialAPIClient
from handlers import JournalEventHandler
from ui import UIManager
from models import ProjectData, SystemSite, ConstructionDepotData, CargoContribution
from plugin_config import PluginConfig
import construction_completion
import fleet_carrier_handler

# Plugin metadata
plugin_name = os.path.basename(os.path.dirname(__file__))
plugin_version = "1.5.1"

# Setup logging per EDMC documentation
# A Logger is used per 'found' plugin to make it easy to include the plugin's
# folder name in the logging output format.
# NB: plugin_name here *must* be the plugin's folder name
logger = logging.getLogger(f'{appname}.{plugin_name}')

# If the Logger has handlers then it was already set up by the core code, else
# it needs setting up here.
if not logger.hasHandlers():
    level = logging.INFO  # So logger.info(...) is equivalent to print()
    
    logger.setLevel(level)
    logger_channel = logging.StreamHandler()
    # Use simple formatter to avoid osthreadid issues
    logger_formatter = logging.Formatter('%(name)s: %(levelname)s - %(message)s')
    logger_channel.setFormatter(logger_formatter)
    logger.addHandler(logger_channel)

# Setup localization
plugin_tl = functools.partial(l10n.translations.tl, context=__file__)

# Set translation function for dialog module
create_project_dialog.set_translation_function(plugin_tl)

# Global state
this = None


class RavencolonialPlugin:
    """Main plugin class to track colonization data"""
    
    def __init__(self):
        # Initialize API client
        self.api_client = RavencolonialAPIClient(
            api_base=PluginConfig.get_api_base(),
            user_agent=PluginConfig.get_user_agent()
        )
        
        # Initialize journal event handler
        self.journal_handler = JournalEventHandler(self)
        
        # Initialize UI manager
        self.ui_manager = UIManager(self)
        
        # Plugin state
        self.cmdr_name: Optional[str] = None
        self.current_system: Optional[str] = None
        self.current_station: Optional[str] = None
        self.current_market_id: Optional[int] = None
        self.current_system_address: Optional[int] = None
        self.star_pos: Optional[List[float]] = None
        self.body_num: Optional[int] = None
        self.body_name: Optional[str] = None
        self.station_type: Optional[str] = None
        self.faction_name: Optional[str] = None
        self.cargo: Dict[str, int] = {}
        self.last_cargo: Dict[str, int] = {}
        self.construction_depot_data: Optional[Dict[str, Any]] = None  # Full ColonisationConstructionDepot event
        self.last_depot_state: Dict[str, int] = {}  # Track previous depot state for diff calculation
        self.is_construction_ship = False
        self.is_docked = False
        self._bodies_fetched = False
        
        # Queue for async API calls
        self.api_queue = queue.Queue()
        self.worker_thread = Thread(target=self._api_worker, daemon=True)
        self.worker_thread.start()
        
        # UI elements are now managed by UIManager
        # These references are kept for backward compatibility
        self.status_label = None
        self.frame = None
        self.create_button = None
        self.project_link_label = None
        self.current_build_id = None
        
        # Build types cache
        self.build_types: List[Dict] = []
        
        # Construction completion handler
        self.completion_handler = construction_completion.ConstructionCompletionHandler(self)
        
        # Fleet Carrier handler
        self.fc_handler = fleet_carrier_handler.FleetCarrierHandler(self)
        
    def _api_worker(self):
        """Background worker thread for API calls"""
        while True:
            try:
                task = self.api_queue.get()
                if task is None:
                    break
                    
                func, args, kwargs = task
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"API call failed: {e}", exc_info=True)
                    # Show error in EDMC status bar asynchronously
                    error_msg = plugin_tl("Ravencolonial API error:") + f" {str(e)}"
                    plug.show_error(error_msg)
                finally:
                    self.api_queue.task_done()
            except Exception as e:
                logger.error(f"Worker thread error: {e}", exc_info=True)
    
    def queue_api_call(self, func, *args, **kwargs):
        """Queue an API call to be executed in background thread"""
        self.api_queue.put((func, args, kwargs))
    
    def get_project(self, system_address: int, market_id: int) -> Optional[Dict]:
        """Get project details for a specific system/station"""
        return self.api_client.get_project(system_address, market_id)
    
    def contribute_cargo(self, build_id: str, cmdr: str, cargo_diff: Dict[str, int]):
        """Submit cargo contribution to Ravencolonial"""
        return self.api_client.contribute_cargo(build_id, cmdr, cargo_diff)
    
    def update_project_supply(self, build_id: str, payload: Dict):
        """Update project supply totals"""
        return self.api_client.update_project_supply(build_id, payload)
    
    def get_commander_projects(self, cmdr: str) -> list:
        """Get all projects for a commander"""
        return self.api_client.get_commander_projects(cmdr)
    
    def get_system_sites(self, system_name: str) -> List[Dict]:
        """Get available construction sites in a system"""
        # We need the system address (ID64) for the v2 API
        if not self.current_system_address:
            logger.debug("No system address available, trying to get from journal")
            self.current_system_address = self.get_system_address_from_journal()
        
        if not self.current_system_address:
            logger.error("Cannot get system sites - no system address available")
            return []
        
        return self.api_client.get_system_sites(self.current_system_address)
    
    def get_system_address_from_journal(self) -> Optional[int]:
        """Get SystemAddress and other data from the most recent Docked event in the journal"""
        logger.debug("get_system_address_from_journal() called")
        try:
            import config
            
            import os
            import glob
            
            # Get journal directory from EDMC config
            journal_dir = None
            
            # Try different config methods
            try:
                journal_dir = config.get_str('journaldir')
                logger.debug(f"Got journal directory from config: {journal_dir}")
            except Exception as e:
                logger.debug(f"Error with config.get_str('journaldir'): {e}")
            
            # If that didn't work, try the default Elite Dangerous location
            if not journal_dir:
                try:
                    default_journal_dir = os.path.join(
                        os.path.expanduser('~'),
                        'Saved Games',
                        'Frontier Developments',
                        'Elite Dangerous'
                    )
                    logger.debug(f"Trying default journal location: {default_journal_dir}")
                    if os.path.exists(default_journal_dir):
                        journal_dir = default_journal_dir
                        logger.debug(f"Using default journal directory: {journal_dir}")
                    else:
                        logger.debug("Default journal directory doesn't exist")
                except Exception as e:
                    logger.debug(f"Error checking default location: {e}")
            
            if not journal_dir or not os.path.exists(journal_dir):
                logger.debug("No valid journal directory found")
                return None
            
            logger.debug(f"Using journal directory: {journal_dir}")
            
            # Find the most recent journal file
            journal_files = glob.glob(os.path.join(journal_dir, 'Journal.*.log'))
            logger.debug(f"Found {len(journal_files)} journal files")
            
            if not journal_files:
                logger.debug("No journal files found")
                return None
            
            # Sort by modification time, most recent first
            journal_files.sort(key=os.path.getmtime, reverse=True)
            
            # Search through up to the 3 most recent journal files
            max_files_to_check = 3
            files_to_check = journal_files[:max_files_to_check]
            logger.debug(f"Will check {len(files_to_check)} journal file(s)")
            
            for file_index, journal_file in enumerate(files_to_check):
                logger.debug(f"Reading journal file {file_index + 1}/{len(files_to_check)}")
                
                try:
                    # Read the file backwards looking for the most recent Docked event
                    with open(journal_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    logger.debug(f"Read {len(lines)} lines from journal file {file_index + 1}")
                    
                    # Search backwards through the lines
                    docked_events_found = 0
                    for line in reversed(lines):
                        try:
                            entry = json.loads(line.strip())
                            if entry.get('event') == 'Docked':
                                docked_events_found += 1
                                
                                system_address = entry.get('SystemAddress')
                                system_name = entry.get('StarSystem')
                                star_pos = entry.get('StarPos')
                                
                                logger.debug(f"Found Docked event in file {file_index + 1}: SystemAddress={system_address}, StarSystem={system_name}")
                                
                                if system_address:
                                    logger.debug(f"Using SystemAddress from journal: {system_address}")
                                    
                                    # Also store system name and star position if available
                                    if system_name and not self.current_system:
                                        logger.debug(f"Storing StarSystem from journal: {system_name}")
                                        self.current_system = system_name
                                    
                                    if star_pos and not self.star_pos:
                                        logger.debug(f"Storing StarPos from journal: {star_pos}")
                                        self.star_pos = star_pos
                                    
                                    return system_address
                        except json.JSONDecodeError:
                            continue
                    
                    logger.debug(f"No valid Docked event in file {file_index + 1} (checked {docked_events_found} Docked events)")
                
                except Exception as e:
                    logger.debug(f"Error reading journal file {file_index + 1}: {e}")
                    continue
            
            logger.debug(f"No valid Docked event with SystemAddress found in any of the {len(files_to_check)} journal files checked")
            return None
        except Exception as e:
            logger.error(f"Exception in get_system_address_from_journal: {type(e).__name__}: {e}", exc_info=e)
            return None
    
    def get_system_bodies(self, system_address: int) -> List[Dict]:
        """Get bodies in a system from Ravencolonial using SystemAddress"""
        return self.api_client.get_system_bodies(system_address)
    
    def get_system_architect(self, system_address: int) -> Optional[str]:
        """Get the architect name for a system if any projects exist"""
        return self.api_client.get_system_architect(system_address)
    
    def check_existing_project(self, system_address: int, market_id: int) -> Optional[Dict]:
        """Check if a project already exists at this location"""
        logger.debug(f"Checking for existing project at system: {system_address}, market: {market_id}")
        # Use the existing get_project method which has the correct endpoint
        return self.get_project(system_address, market_id)
    
    def create_project(self, project_data: Dict[str, Any]) -> Optional[Dict]:
        """Create a new colonization project"""
        return self.api_client.create_project(project_data)
    
    def handle_cargo_depot(self, entry: Dict[str, Any]):
        """Handle CargoDepot journal event"""
        return self.journal_handler.handle_cargo_depot(entry)
    
    def handle_colonisation_construction_depot(self, entry: Dict[str, Any]):
        """Handle ColonisationConstructionDepot journal event"""
        return self.journal_handler.handle_colonisation_construction_depot(entry)
    
    def handle_colonisation_contribution(self, entry: Dict[str, Any]):
        """Handle ColonisationContribution journal event"""
        return self.journal_handler.handle_colonisation_contribution(entry)
    
    def handle_market(self, entry: Dict[str, Any]):
        """Handle Market journal event"""
        return self.journal_handler.handle_market(entry)
    
    def get_market_data(self) -> Optional[List[Dict[str, Any]]]:
        """Get current market data from EDMC"""
        try:
            # EDMC provides market data through the monitor's market file
            # This is a simplified implementation - in practice you'd need to
            # access EDMC's market data through the appropriate API
            import json
            import os
            
            # Get the market file path from EDMC's config
            journal_dir = config.get_str('journaldir') or None
            if not journal_dir:
                logger.warning("No journal directory configured")
                return None
            
            # Look for the latest market file
            market_files = [f for f in os.listdir(journal_dir) if f.startswith('Market.') and f.endswith('.json')]
            if not market_files:
                logger.warning("No market files found")
                return None
            
            # Get the most recent market file
            latest_file = sorted(market_files)[-1]
            market_path = os.path.join(journal_dir, latest_file)
            
            with open(market_path, 'r') as f:
                market_data = json.load(f)
            
            # Extract items from market data
            items = market_data.get('Items', [])
            logger.debug(f"Loaded {len(items)} items from market file")
            
            return items
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            return None
    
    def update_status(self, message: str):
        """Update the UI status label"""
        return self.ui_manager.update_status(message)
    
    def update_create_button(self):
        """Enable/disable create button based on docking status and existing projects"""
        return self.ui_manager.update_create_button()
    
    def get_system_address_from_journal(self) -> Optional[int]:
        """Get SystemAddress and other data from the most recent Docked event in the journal"""
        logger.debug("get_system_address_from_journal() called")
        try:
            import config
            
            import os
            import glob
            import json
            
            # Get journal directory from EDMC config
            journal_dir = None
            
            # Try different config methods
            try:
                journal_dir = config.get_str('journaldir')
                logger.debug(f"Got journal directory from config: {journal_dir}")
            except Exception as e:
                logger.debug(f"Error with config.get_str('journaldir'): {e}")
            
            # If that didn't work, try the default Elite Dangerous location
            if not journal_dir:
                try:
                    default_journal_dir = os.path.join(
                        os.path.expanduser('~'),
                        'Saved Games',
                        'Frontier Developments',
                        'Elite Dangerous'
                    )
                    logger.debug(f"Trying default journal location: {default_journal_dir}")
                    if os.path.exists(default_journal_dir):
                        journal_dir = default_journal_dir
                        logger.debug(f"Using default journal directory: {journal_dir}")
                    else:
                        logger.debug("Default journal directory doesn't exist")
                except Exception as e:
                    logger.debug(f"Error checking default location: {e}")
            
            if not journal_dir or not os.path.exists(journal_dir):
                logger.debug("No valid journal directory found")
                return None
            
            logger.debug(f"Using journal directory: {journal_dir}")
            
            # Find the most recent journal file
            journal_files = glob.glob(os.path.join(journal_dir, 'Journal.*.log'))
            logger.debug(f"Found {len(journal_files)} journal files")
            
            if not journal_files:
                logger.debug("No journal files found")
                return None
            
            # Sort by modification time, most recent first
            journal_files.sort(key=os.path.getmtime, reverse=True)
            
            # Search through up to the 3 most recent journal files
            max_files_to_check = 3
            files_to_check = journal_files[:max_files_to_check]
            logger.debug(f"Will check {len(files_to_check)} journal file(s)")
            
            for file_index, journal_file in enumerate(files_to_check):
                logger.debug(f"Reading journal file {file_index + 1}/{len(files_to_check)}")
                
                try:
                    # Read the file backwards looking for the most recent Docked event
                    with open(journal_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    logger.debug(f"Read {len(lines)} lines from journal file {file_index + 1}")
                    
                    # Search backwards through the lines
                    docked_events_found = 0
                    for line in reversed(lines):
                        try:
                            entry = json.loads(line.strip())
                            if entry.get('event') == 'Docked':
                                docked_events_found += 1
                                
                                system_address = entry.get('SystemAddress')
                                system_name = entry.get('StarSystem')
                                star_pos = entry.get('StarPos')
                                
                                logger.debug(f"Found Docked event in file {file_index + 1}: SystemAddress={system_address}, StarSystem={system_name}")
                                
                                if system_address:
                                    logger.debug(f"Using SystemAddress from journal: {system_address}")
                                    
                                    # Also store system name and star position if available
                                    if system_name and not self.current_system:
                                        logger.debug(f"Storing StarSystem from journal: {system_name}")
                                        self.current_system = system_name
                                    
                                    if star_pos and not self.star_pos:
                                        logger.debug(f"Storing StarPos from journal: {star_pos}")
                                        self.star_pos = star_pos
                                    
                                    return system_address
                        except json.JSONDecodeError:
                            continue
                    
                    logger.debug(f"No valid Docked event in file {file_index + 1} (checked {docked_events_found} Docked events)")
                
                except Exception as e:
                    logger.debug(f"Error reading journal file {file_index + 1}: {e}")
                    continue
            
            logger.debug(f"No valid Docked event with SystemAddress found in any of the {len(files_to_check)} journal files checked")
            return None
        except Exception as e:
            logger.error(f"Exception in get_system_address_from_journal: {type(e).__name__}: {e}", exc_info=True)
            return None


def plugin_start3(plugin_dir: str) -> str:
    """
    Load the plugin.
    
    :param plugin_dir: The plugin directory
    :return: Plugin name
    """
    global this
    try:
        this = RavencolonialPlugin()
        logger.info(f"Ravencolonial-EDMC v{PluginConfig.VERSION} loaded")
        return plugin_name
    except Exception as e:
        logger.error(f"Failed to initialize: {e}", exc_info=True)
        raise


def plugin_stop() -> None:
    """
    Unload the plugin.
    """
    global this
    if this:
        # Signal worker thread to stop
        this.api_queue.put(None)
        # Wait for worker thread to finish (recommended by EDMC docs)
        if this.worker_thread and this.worker_thread.is_alive():
            this.worker_thread.join(timeout=5)  # 5 second timeout to avoid hanging
        logger.info(f"{PluginConfig.NAME} stopped")


def plugin_prefs(parent: nb.Notebook, cmdr: str, is_beta: bool) -> nb.Frame:
    """
    Create settings page for the plugin.
    
    :param parent: The notebook parent
    :param cmdr: Commander name
    :param is_beta: Whether in beta
    :return: Settings frame
    """
    global this
    logger.info("Creating plugin preferences page")
    
    # Create a frame for the settings (use nb.Frame as EDMC expects)
    frame = nb.Frame(parent)
    
    # Title
    title_label = ttk.Label(frame, text="Ravencolonial Plugin Settings", font=('TkDefaultFont', 12, 'bold'))
    title_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=10, pady=(10, 20))
    
    # API Key setting
    api_key_label = ttk.Label(frame, text="Ravencolonial API Key:")
    api_key_label.grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
    
    try:
        api_key_value = config.get_str('ravencolonial_api_key') or ''
    except:
        api_key_value = ''
    
    api_key_var = tk.StringVar(value=api_key_value)
    api_key_entry = ttk.Entry(frame, textvariable=api_key_var, width=40, show="*")
    api_key_entry.grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)
    
    # API Key help text
    api_key_help = ttk.Label(frame, text="Get your API key from Ravencolonial account settings", 
                             font=('TkDefaultFont', 9), foreground='gray')
    api_key_help.grid(row=2, column=1, sticky=tk.W, padx=10, pady=(0, 10))
    
    # Stealth Mode checkbox
    try:
        stealth_value = config.get_bool('ravencolonial_stealth_mode')
    except:
        stealth_value = False
    
    stealth_var = tk.BooleanVar(value=stealth_value)
    stealth_check = ttk.Checkbutton(frame, text="Stealth Mode", variable=stealth_var)
    stealth_check.grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=10, pady=5)
    
    # Stealth Mode help text
    stealth_help = ttk.Label(frame, text="When enabled, stops sending Fleet Carrier commodity data to Ravencolonial", 
                             font=('TkDefaultFont', 9), foreground='gray')
    stealth_help.grid(row=4, column=1, sticky=tk.W, padx=10, pady=(0, 10))
    
    # Save button
    def save_settings():
        """Save the settings to EDMC config"""
        config.set('ravencolonial_api_key', api_key_var.get())
        config.set('ravencolonial_stealth_mode', stealth_var.get())
        
        # Update API client credentials if plugin is loaded
        if this and api_key_var.get():
            this.api_client.set_credentials(cmdr, api_key_var.get())
        
        # Update Fleet Carrier stealth mode if plugin is loaded
        if this and hasattr(this, 'fc_handler'):
            this.fc_handler.set_stealth_mode(stealth_var.get())
    
    save_button = ttk.Button(frame, text="Save Settings", command=save_settings)
    save_button.grid(row=5, column=0, columnspan=2, pady=20)
    
    logger.info("Plugin preferences page created successfully")
    return frame


def plugin_app_prefs_cmdr(parent: nb.Notebook, cmdr: str, is_beta: bool) -> Optional[nb.Frame]:
    """
    Alternative preferences function for EDMC compatibility.
    Some EDMC versions call this instead of plugin_prefs.
    """
    return plugin_prefs(parent, cmdr, is_beta)


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    """
    Handle preference changes. Called when user changes settings.
    Refresh UI elements if language changed.
    
    :param cmdr: Current commander name
    :param is_beta: Whether game is in beta
    """
    global this
    if this:
        # Update button text in case language changed
        this.update_create_button()


def plugin_app(parent: tk.Frame) -> tk.Frame:
    """
    Create a frame for the main EDMC window.
    
    :param parent: The parent frame
    :return: A tk.Frame for display in main window
    """
    global this
    
    if not this:
        return tk.Frame(parent)
    
    # Use the UI manager to create the plugin frame
    frame = this.ui_manager.create_plugin_frame(parent)
    
    return frame


def journal_entry(
    cmdr: str, is_beta: bool, system: str, station: str, entry: Dict[str, Any], state: Dict[str, Any]
) -> Optional[str]:
    """
    Handle journal entry events.
    
    :param cmdr: Commander name
    :param is_beta: Whether in beta
    :param system: Current system
    :param station: Current station
    :param entry: The journal entry
    :param state: Current game state
    :return: Optional status message
    """
    global this
    
    if not this:
        return None
    
    # Update commander and location
    this.cmdr_name = cmdr
    this.current_system = system
    this.current_station = station
    
    logger.debug(f"Journal entry - cmdr: {cmdr}, system: {system}, station: {station}")
    
    # Initialize Fleet Carrier handler on first commander event
    logger.debug(f"FC init check: cmdr={cmdr}, has_initialized={hasattr(this.fc_handler, '_initialized')}")
    if cmdr and not hasattr(this.fc_handler, '_initialized'):
        logger.info(f"Initializing Fleet Carrier handler for {cmdr}")
        # Set API client credentials for Fleet Carrier operations
        api_key = config.get_str('ravencolonial_api_key') or ''
        logger.debug(f"API key present: {bool(api_key)}")
        if api_key:
            this.api_client.set_credentials(cmdr, api_key)
            logger.debug("API credentials set")
        
        this.fc_handler.initialize_fcs(cmdr)
        
        # Initialize current station state from game state (in case already docked when EDMC starts)
        if state:
            station_type = state.get('StationType')
            market_id = state.get('MarketID')
            if station_type and market_id:
                this.fc_handler.current_station_type = station_type
                this.fc_handler.current_market_id = market_id
                logger.info(f"Initialized FC handler with current station: {station_type}, marketID: {market_id}")
        
        this.fc_handler._initialized = True
        logger.info("Fleet Carrier handler initialization complete")
    
    event = entry.get('event')
    
    # Handle different events
    if event == 'Docked':
        logger.info(f"Docked at {station}, MarketID: {entry.get('MarketID')}")
        this.current_market_id = entry.get('MarketID')
        this.current_system_address = entry.get('SystemAddress')
        this.star_pos = entry.get('StarPos')
        this.body_num = entry.get('BodyID')
        this.body_name = entry.get('Body')
        this.station_type = entry.get('StationType')
        this.faction_name = entry.get('StationFaction', {}).get('Name')
        this.is_docked = True
        # Check if this is a colonization ship - they appear as SurfaceStation but have ColonisationShip in the name
        station_name = entry.get('StationName', '')
        this.is_construction_ship = 'ColonisationShip' in station_name
        logger.debug(f"Docked details - StationType: {this.station_type}, is_construction_ship: {this.is_construction_ship}")
        
        # Handle Fleet Carrier docking
        this.fc_handler.handle_docked_event(entry)
        
        this.update_status(f"Docked at {station}")
        this.update_create_button()
        
    elif event == 'Undocked':
        logger.info(f"Undocked from {station}")
        this.is_docked = False
        this.is_construction_ship = False
        this.current_market_id = None
        this._bodies_fetched = False  # Reset flag for next docking
        this.last_depot_state = {}  # Reset depot state for next docking
        this.update_status(f"Undocked from {station}")
        this.update_create_button()
        
    elif event == 'Location':
        logger.info(f"Location event - system: {system}, station: {station}")
        this.current_system_address = entry.get('SystemAddress')
        this.star_pos = entry.get('StarPos')
        if entry.get('Docked'):
            this.current_market_id = entry.get('MarketID')
            this.body_num = entry.get('BodyID')
            this.body_name = entry.get('Body')
            this.station_type = entry.get('StationType')
            this.is_docked = True
            # Check if this is a colonization ship - they appear as SurfaceStation but have ColonisationShip in the name
            station_name = entry.get('StationName', '')
            this.is_construction_ship = 'ColonisationShip' in station_name
            logger.info(f"Location event - docked at {station}, StationType: {this.station_type}, StationName: {station_name}, is_construction_ship: {this.is_construction_ship}")
            this.update_create_button()
        else:
            this.is_docked = False
            this.is_construction_ship = False
            this.current_market_id = None
            this.update_create_button()
            
    elif event == 'CargoDepot':
        this.handle_cargo_depot(entry)
        
    elif event == 'Market':
        this.handle_market(entry)
        # Handle Fleet Carrier market updates
        # Disabled for now - MarketBuy/MarketSell events handle commodity updates
        # this.fc_handler.handle_market_event(entry)
        
    elif event == 'MarketBuy':
        # Handle Fleet Carrier purchases
        this.fc_handler.handle_marketbuy_event(entry)
        
    elif event == 'MarketSell':
        # Handle Fleet Carrier sales
        logger.debug(f"MarketSell event received: {entry}")
        result = this.fc_handler.handle_marketsell_event(entry)
        logger.debug(f"MarketSell handler returned: {result}")
        
    elif event == 'CargoTransfer':
        # Handle Fleet Carrier cargo transfers
        logger.debug(f"CargoTransfer event received: {entry}")
        result = this.fc_handler.handle_cargotransfer_event(entry)
        logger.debug(f"CargoTransfer handler returned: {result}")
        
    elif event == 'Cargo':
        # Update cargo manifest
        inventory = entry.get('Inventory', [])
        this.cargo = {item['Name'].replace('_name', ''): item['Count'] for item in inventory}
    
    elif event == 'ColonisationConstructionDepot':
        logger.debug("ColonisationConstructionDepot event received")
        # Check stealth mode
        try:
            stealth_mode = config.get_bool('ravencolonial_stealth_mode')
        except:
            stealth_mode = False
        
        if not stealth_mode:
            this.handle_colonisation_construction_depot(entry)
        else:
            logger.debug("Stealth mode enabled - not sending colonization depot data")
    
    elif event == 'ColonisationContribution':
        logger.debug("ColonisationContribution event received")
        # Check stealth mode
        try:
            stealth_mode = config.get_bool('ravencolonial_stealth_mode')
        except:
            stealth_mode = False
        
        if not stealth_mode:
            this.handle_colonisation_contribution(entry)
        else:
            logger.debug("Stealth mode enabled - not sending colonization contribution data")
    
    return None


def capi_fleetcarrier(data: CAPIData) -> Optional[str]:
    """
    Handle Fleet Carrier CAPI data from Frontier.
    Called when EDMC fetches fresh FC data after CarrierStats journal events.
    
    :param data: CAPIData object with FC information
    :return: Optional status message
    """
    global this
    
    if not this or not this.fc_handler:
        return None
    
    try:
        # Extract FC callsign and market ID
        if 'name' not in data or 'callsign' not in data['name']:
            logger.warning("CAPI FC data missing name/callsign")
            return None
        
        callsign = data['name']['callsign']
        logger.info(f"Received CAPI data for Fleet Carrier: {callsign}")
        
        # Get market ID from current state (CAPI doesn't provide market ID directly)
        market_id = this.fc_handler.current_market_id
        if not market_id:
            logger.warning("No current market ID - cannot process CAPI FC data")
            return None
        
        # Check if this FC is linked
        if market_id not in this.fc_handler.linked_fcs:
            logger.debug(f"CAPI data for unlinked FC {callsign} ({market_id}) - ignoring")
            return None
        
        # Check stealth mode
        if this.fc_handler.stealth_mode:
            logger.info(f"Stealth mode enabled - ignoring CAPI data for FC {callsign}")
            return None
        
        # Extract cargo data from CAPI
        cargo_list = data.get('cargo', [])
        if not cargo_list:
            logger.info(f"No cargo data in CAPI response for FC {callsign}")
            return None
        
        # Convert CAPI cargo format to our format
        # CAPI format: [{"commodity": "name", "qty": 1, "value": X, ...}, ...]
        # Our format: {"commodity": total_quantity, ...}
        cargo_totals = {}
        for item in cargo_list:
            commodity = item.get('commodity', '').lower()
            qty = item.get('qty', 0)
            if commodity:
                cargo_totals[commodity] = cargo_totals.get(commodity, 0) + qty
        
        logger.info(f"CAPI FC cargo for {callsign}: {len(cargo_totals)} commodity types, {sum(cargo_totals.values())} total units")
        logger.debug(f"CAPI cargo details: {cargo_totals}")
        
        # Update FC cargo on server
        this.fc_handler.update_fc_cargo_from_capi(market_id, cargo_totals)
        
    except Exception as e:
        logger.error(f"Error processing CAPI FC data: {e}", exc_info=True)
    
    return None


def open_url(url: str):
    """Open URL in browser"""
    webbrowser.open(url)


def open_project_link():
    """Open the existing project in browser"""
    global this
    if this and this.current_build_id:
        url = f"https://ravencolonial.com/#build={this.current_build_id}"
        logger.info(f"Opening project page: {url}")
        open_url(url)


def open_create_dialog(parent):
    """Open the Create Project dialog"""
    global this
    if this:
        try:
            dialog = create_project_dialog.CreateProjectDialog(parent, this)
        except Exception as e:
            logger.error(f"Failed to open create dialog: {e}", exc_info=True)
            messagebox.showerror(plugin_tl("Error"), plugin_tl("Failed to open dialog:") + f" {str(e)}")
