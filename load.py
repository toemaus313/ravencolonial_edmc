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
import requests
import json
import urllib.parse
import logging
import os
import functools
import l10n
import plug
import create_project_dialog
import webbrowser

# Plugin metadata
plugin_name = os.path.basename(os.path.dirname(__file__))
plugin_version = "1.3.0"

# Setup logging
logger = logging.getLogger(f'{appname}.{plugin_name}')

# If the Logger has handlers then it was already set up by the core code, else
# it needs setting up here.
if not logger.hasHandlers():
    level = logging.INFO  # So logger.info(...) is equivalent to print()
    
    logger.setLevel(level)
    logger_channel = logging.StreamHandler()
    logger_formatter = logging.Formatter(f'%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d:%(funcName)s: %(message)s')
    logger_formatter.default_time_format = '%Y-%m-%d %H:%M:%S'
    logger_formatter.default_msec_format = '%s.%03d'
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
        # Allow custom API URL from config, otherwise use default
        self.api_base = config.get_str("ravencolonial_api_url") or "https://ravencolonial100-awcbdvabgze4c5cq.canadacentral-01.azurewebsites.net"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': f'EDMC-Ravencolonial/{plugin_version}',
            'Content-Type': 'application/json'
        })
        
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
        
        # UI elements
        self.status_label: Optional[tk.Label] = None
        self.frame: Optional[tk.Frame] = None
        self.create_button: Optional[tk.Button] = None
        self.project_link_label: Optional[tk.Label] = None
        self.current_build_id: Optional[str] = None
        
        # Build types cache
        self.build_types: List[Dict] = []
        
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
        try:
            url = f"{self.api_base}/api/system/{system_address}/{market_id}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get project: {e}")
            return None
    
    def contribute_cargo(self, build_id: str, cmdr: str, cargo_diff: Dict[str, int]):
        """Submit cargo contribution to Ravencolonial (for commander attribution)"""
        try:
            url = f"{self.api_base}/api/project/{build_id}/contribute/{urllib.parse.quote(cmdr)}"
            logger.debug(f"Contribution URL: {url}")
            logger.debug(f"Contribution payload: {cargo_diff}")
            response = self.session.post(url, json=cargo_diff, timeout=10)
            logger.debug(f"Contribution response status: {response.status_code}")
            response.raise_for_status()
            logger.info(f"Contributed cargo to project {build_id}: {cargo_diff}")
            return True
        except Exception as e:
            logger.error(f"Contribution error: {e}")
            logger.error(f"Failed to contribute cargo: {e}")
            return False
    
    def update_project_supply(self, build_id: str, payload: Dict):
        """Update project supply totals (for the 'Need' column)"""
        try:
            url = f"{self.api_base}/api/project/{build_id}"
            logger.debug(f"Update supply URL: {url}")
            logger.debug(f"Update supply payload: {json.dumps(payload)}")
            response = self.session.post(url, json=payload, timeout=10)
            logger.debug(f"Update supply response status: {response.status_code}")
            logger.debug(f"Update supply response body: {response.text}")
            response.raise_for_status()
            logger.info(f"Updated project supply for {build_id}")
            return True
        except Exception as e:
            logger.error(f"Update supply error: {e}")
            logger.error(f"Failed to update project supply: {e}")
            return False
    
    def get_commander_projects(self, cmdr: str) -> list:
        """Get all projects for a commander"""
        try:
            url = f"{self.api_base}/api/cmdr/{cmdr}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get commander projects: {e}")
            return []
    
    def get_system_sites(self, system_name: str) -> List[Dict]:
        """Get available construction sites in a system"""
        logger.debug(f"get_system_sites called for system: {system_name}")
        
        # We need the system address (ID64) for the v2 API
        if not self.current_system_address:
            logger.debug("No system address available, trying to get from journal")
            self.current_system_address = self.get_system_address_from_journal()
        
        if not self.current_system_address:
            logger.error("Cannot get system sites - no system address available")
            return []
        
        try:
            url = f"{self.api_base}/api/v2/system/{self.current_system_address}/sites"
            logger.debug(f"Fetching sites from URL: {url}")
            response = self.session.get(url, timeout=10)
            logger.debug(f"Sites API response status: {response.status_code}")
            if response.status_code != 200:
                logger.debug(f"Sites API response body: {response.text}")
            response.raise_for_status()
            sites = response.json()
            logger.debug(f"Successfully fetched {len(sites)} sites: {sites}")
            return sites
        except Exception as e:
            logger.error(f"Failed to get system sites: {e}")
            logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            return []
    
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
        try:
            url = f"{self.api_base}/api/v2/system/{system_address}/bodies"
            logger.debug(f"Bodies URL: {url}")
            response = self.session.get(url, timeout=10)
            logger.debug(f"Bodies response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            
            # Ravencolonial returns an array of body objects
            bodies = data if isinstance(data, list) else []
            logger.debug(f"Extracted {len(bodies)} bodies from response")
            
            return bodies
        except Exception as e:
            logger.error(f"Failed to get system bodies: {e}")
            return []
    
    def check_existing_project(self, system_address: int, market_id: int) -> Optional[Dict]:
        """Check if a project already exists at this location"""
        logger.debug(f"Checking for existing project at system: {system_address}, market: {market_id}")
        # Use the existing get_project method which has the correct endpoint
        return self.get_project(system_address, market_id)
    
    def create_project(self, project_data: Dict[str, Any]) -> Optional[Dict]:
        """Create a new colonization project"""
        url = f"{self.api_base}/api/project/"
        
        # Always log what we're sending
        logger.error("=" * 80)
        logger.error("CREATING PROJECT - REQUEST DETAILS:")
        logger.error(f"URL: {url}")
        logger.error(f"Data being sent:\n{json.dumps(project_data, indent=2)}")
        logger.error("=" * 80)
        
        try:
            response = self.session.put(url, json=project_data, timeout=10)
            
            # Always log the response
            logger.error(f"RESPONSE STATUS: {response.status_code}")
            logger.error(f"RESPONSE BODY:\n{response.text}")
            logger.error("=" * 80)
            
            if not response.ok:
                return None
            
            result = response.json()
            logger.info(f"SUCCESS! Created project: {result.get('buildId')}")
            return result
            
        except Exception as e:
            logger.error(f"EXCEPTION while creating project: {e}", exc_info=True)
            return None
    
    def handle_cargo_depot(self, entry: Dict[str, Any]):
        """Handle CargoDepot journal event (cargo delivered to construction)"""
        if not self.cmdr_name or not self.current_market_id or not self.current_system_address:
            return
        
        # Get current project
        project = self.get_project(self.current_system_address, self.current_market_id)
        if not project:
            logger.debug("No project found for cargo depot delivery")
            return
        
        build_id = project.get('buildId')
        if not build_id:
            logger.debug("Project found but no buildId")
            return
        
        # Check if this is a construction depot delivery
        mission_id = entry.get('MissionID')
        cargo_type = entry.get('Type', '').replace('_name', '')
        count = entry.get('Count', 0)
        
        # Queue the contribution
        if entry.get('SubType') == 'Deliver':
            cargo_diff = {cargo_type: count}
            self.queue_api_call(self.contribute_cargo, build_id, self.cmdr_name, cargo_diff)
            self.update_status(f"Delivered {count}x {cargo_type}")
    
    def handle_colonisation_construction_depot(self, entry: Dict[str, Any]):
        """Handle ColonisationConstructionDepot journal event (status update)"""
        logger.debug(f"ColonisationConstructionDepot - cmdr: {self.cmdr_name}, market: {self.current_market_id}, system: {self.current_system_address}")
        logger.debug(f"Event keys: {list(entry.keys())}")
        
        # Extract MarketID from the event if we don't have it yet
        # This handles the case where EDMC starts while already docked
        event_market_id = entry.get('MarketID')
        if event_market_id and not self.current_market_id:
            logger.debug(f"Extracting MarketID from event: {event_market_id}")
            self.current_market_id = event_market_id
        
        # Try to get SystemAddress from event if we don't have it
        event_system_address = entry.get('SystemAddress')
        if event_system_address and not self.current_system_address:
            logger.debug(f"Extracting SystemAddress from event: {event_system_address}")
            self.current_system_address = event_system_address
        
        # If we still don't have system address, fetch from journal
        if not self.current_system_address:
            logger.debug("No SystemAddress in event or state, fetching from journal")
            self.current_system_address = self.get_system_address_from_journal()
            if self.current_system_address:
                logger.debug(f"Got system address from journal: {self.current_system_address}")
        
        if not self.cmdr_name:
            logger.warning("Missing commander name, cannot process ColonisationConstructionDepot event")
            return
        
        # Store the full construction depot data for project creation
        self.construction_depot_data = entry
        logger.info(f"Captured ColonisationConstructionDepot data for {self.current_station}")
        
        # Calculate current needed amounts (RequiredAmount - ProvidedAmount)
        resources = entry.get('ResourcesRequired', [])
        needed = {}
        max_need = 0
        for resource in resources:
            commodity_name = resource.get('Name', '').replace('$', '').replace('_name;', '').lower()
            required = resource.get('RequiredAmount', 0)
            provided = resource.get('ProvidedAmount', 0)
            still_needed = required - provided
            if commodity_name and required > 0:
                needed[commodity_name] = still_needed
                max_need += required
        
        # Check if totals changed since last time
        if self.last_depot_state != needed and needed:
            # Update the project with current needed amounts
            if self.current_system_address and self.current_market_id:
                logger.debug("Depot needs changed - updating project")
                logger.debug(f"Max need: {max_need}")
                project = self.get_project(self.current_system_address, self.current_market_id)
                if project and project.get('buildId'):
                    build_id = project['buildId']
                    logger.info(f"Updating project {build_id} with depot state changes")
                    # Send full needed amounts with maxNeed (ProjectUpdate format)
                    payload = {
                        "buildId": build_id,
                        "commodities": needed,
                        "maxNeed": max_need
                    }
                    self.queue_api_call(self.update_project_supply, build_id, payload)
        else:
            if self.last_depot_state == needed:
                logger.debug("Depot state unchanged - skipping supply update")
        
        # Store current state for next comparison
        self.last_depot_state = needed
        
        # If we're receiving this event, we're definitely at a colonization ship
        # Update construction ship status and button state
        logger.debug(f"State before update - is_docked: {self.is_docked}, market_id: {self.current_market_id}, is_construction_ship: {self.is_construction_ship}")
        
        if not self.is_docked:
            self.is_docked = True
        if not self.is_construction_ship:
            self.is_construction_ship = True
        
        logger.debug("Set is_construction_ship and is_docked to True")
        self.update_create_button()
    
    def handle_colonisation_contribution(self, entry: Dict[str, Any]):
        """Handle ColonisationContribution journal event (actual cargo deliveries)"""
        if not self.cmdr_name or not self.current_market_id:
            logger.warning(f"Missing state for contribution - cmdr: {self.cmdr_name}, market: {self.current_market_id}")
            return
        
        # Get system address if we don't have it
        if not self.current_system_address:
            logger.debug("No system address, fetching from journal")
            self.current_system_address = self.get_system_address_from_journal()
            if not self.current_system_address:
                logger.warning("Could not get system address from journal, aborting contribution")
                return
            logger.debug(f"Got system address from journal: {self.current_system_address}")
        
        # Get current project to get buildId
        project = self.get_project(self.current_system_address, self.current_market_id)
        if not project:
            logger.warning(f"No project found for market {self.current_market_id}")
            return
        
        build_id = project.get('buildId')
        if not build_id:
            logger.warning("Project found but no buildId")
            return
        
        # Extract delivered commodities from Contributions
        contributions = entry.get('Contributions', [])
        if not contributions:
            logger.debug("No contributions in this event")
            return
        
        # Build cargo diff from contributions
        cargo_diff = {}
        for contribution in contributions:
            # Remove the _name suffix and $ prefix from commodity names
            commodity_name = contribution.get('Name', '').replace('$', '').replace('_name;', '').lower()
            delivered_amount = contribution.get('Amount', 0)
            if commodity_name and delivered_amount > 0:
                cargo_diff[commodity_name] = delivered_amount
        
        if cargo_diff:
            total_delivered = sum(cargo_diff.values())
            logger.info(f"Submitting {total_delivered} units to project {build_id}: {cargo_diff}")
            # Update commander contribution (for bar graph)
            # Note: Project supply totals are updated via ColonisationConstructionDepot diffs
            self.queue_api_call(self.contribute_cargo, build_id, self.cmdr_name, cargo_diff)
            self.update_status(f"Delivered {total_delivered} units to colonization")
    
    def handle_market(self, entry: Dict[str, Any]):
        """Handle Market journal event"""
        # Market data could be used to sync current needs
        pass
    
    def update_status(self, message: str):
        """Update the UI status label"""
        if self.status_label:
            self.status_label['text'] = message
            logger.info(message)
    
    def update_create_button(self):
        """Enable/disable create button based on docking status and existing projects"""
        logger.debug(f"update_create_button - is_docked: {self.is_docked}, market_id: {self.current_market_id}, is_construction_ship: {self.is_construction_ship}")
        
        if not self.create_button:
            return
        
        # Check if we're at a construction ship
        if self.is_docked and self.current_market_id and self.is_construction_ship:
            # Get system address if we don't have it
            if not self.current_system_address:
                logger.debug("No system_address, fetching from journal for project check")
                self.current_system_address = self.get_system_address_from_journal()
            
            # Check for existing project
            if self.current_system_address:
                existing_project = self.check_existing_project(self.current_system_address, self.current_market_id)
            else:
                logger.warning("Could not get system_address, unable to check for existing project")
                existing_project = None
            
            if existing_project:
                # Project exists - change button to open build page
                build_id = existing_project.get('buildId', '')
                build_name = existing_project.get('buildName', 'Unknown')
                logger.info(f"Found existing project: {build_name} ({build_id})")
                
                self.create_button['state'] = tk.NORMAL
                self.create_button['text'] = plugin_tl("🌐 Open Build Page")
                # Change button command to open project link
                self.create_button['command'] = lambda: open_project_link()
                
                if self.project_link_label:
                    link_text = f"{build_name}"
                    self.project_link_label['text'] = link_text
                    self.project_link_label['fg'] = 'blue'
                    self.project_link_label['cursor'] = 'hand2'
                
                # Store build_id for click handler
                self.current_build_id = build_id
            else:
                # No project exists - fetch body data then enable button
                logger.info("No existing project found")
                
                # Clear project link
                if self.project_link_label:
                    self.project_link_label['text'] = ""
                    self.current_build_id = None
                
                # Fetch body data in background for future use
                if self.current_system and not hasattr(self, '_bodies_fetched'):
                    logger.debug("Pre-fetching body data for Create dialog")
                    # Get system address from journal if needed
                    if not self.current_system_address:
                        self.current_system_address = self.get_system_address_from_journal()
                    self._bodies_fetched = True
                
                # Enable create button and restore original command
                logger.debug("Enabling Create Project button")
                self.create_button['state'] = tk.NORMAL
                self.create_button['text'] = plugin_tl("🚧 Create Project")
                # Restore original command to open create dialog
                if self.frame:
                    self.create_button['command'] = lambda: open_create_dialog(self.frame.master)
        else:
            # Not at construction ship - disable button and restore original command
            logger.debug("Disabling Create Project button")
            self.create_button['state'] = tk.DISABLED
            
            # Restore original command to open create dialog
            if self.frame:
                self.create_button['command'] = lambda: open_create_dialog(self.frame.master)
            
            if self.project_link_label:
                self.project_link_label['text'] = ""
                self.current_build_id = None
            
            if not self.is_docked:
                self.create_button['text'] = plugin_tl("Create Project (Dock First)")
            elif not self.is_construction_ship:
                self.create_button['text'] = plugin_tl("Create Project (Dock at Construction Ship)")
            else:
                self.create_button['text'] = plugin_tl("Create Project")


def plugin_start3(plugin_dir: str) -> str:
    """
    Load the plugin.
    
    :param plugin_dir: The plugin directory
    :return: Plugin name
    """
    global this
    this = RavencolonialPlugin()
    logger.info(f"{plugin_name} v{plugin_version} loaded")
    return plugin_name


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
        logger.info(f"{plugin_name} stopped")


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
    
    frame = tk.Frame(parent)
    this.frame = frame
    
    # Status label
    this.status_label = tk.Label(frame, text=plugin_tl("Ravencolonial: Ready"))
    this.status_label.pack(side=tk.LEFT, padx=5)
    
    # Project link label (shows when project exists)
    this.project_link_label = tk.Label(frame, text="", cursor="hand2", fg='blue')
    this.project_link_label.pack(side=tk.LEFT, padx=5)
    this.project_link_label.bind("<Button-1>", lambda e: open_project_link())
    this.current_build_id = None
    
    # Create project button
    this.create_button = tk.Button(
        frame, 
        text=plugin_tl("Create Project (Dock First)"),
        command=lambda: open_create_dialog(parent),
        state=tk.DISABLED
    )
    this.create_button.pack(side=tk.LEFT, padx=5)
    
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
