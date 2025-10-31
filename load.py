"""
EDMC Plugin for Ravencolonial Colonization Tracking

This plugin tracks Elite Dangerous colonization activities and sends data
to Ravencolonial (ravencolonial.com) by grinning2001
"""

import tkinter as tk
from tkinter import ttk, messagebox
import myNotebook as nb
from config import appname, config
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

# Plugin metadata
plugin_name = os.path.basename(os.path.dirname(__file__))
plugin_version = "1.3.0"

# Setup logging using config module
logger = PluginConfig.setup_logging()

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
    this = RavencolonialPlugin()
    logger.info(f"{PluginConfig.NAME} v{PluginConfig.VERSION} loaded")
    return PluginConfig.NAME


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


# No settings page needed - plugin works automatically without configuration
# def plugin_prefs(parent: nb.Notebook, cmdr: str, is_beta: bool) -> Optional[tk.Frame]:
#     """
#     Create a preferences frame for the plugin.
#     Would be used if plugin needed user-configurable settings.
#     """
#     pass


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
        
    elif event == 'Cargo':
        # Update cargo manifest
        inventory = entry.get('Inventory', [])
        this.cargo = {item['Name'].replace('_name', ''): item['Count'] for item in inventory}
    
    elif event == 'ColonisationConstructionDepot':
        logger.debug("ColonisationConstructionDepot event received")
        this.handle_colonisation_construction_depot(entry)
    
    elif event == 'ColonisationContribution':
        logger.debug("ColonisationContribution event received")
        this.handle_colonisation_contribution(entry)
    
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
