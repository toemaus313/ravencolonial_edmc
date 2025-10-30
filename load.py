"""
EDMC Plugin for Ravencolonial Colonization Tracking

This plugin tracks Elite Dangerous colonization activities and sends data
to Ravencolonial (ravencolonial.com) so users don't need SRVSurvey running.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import myNotebook as nb
from config import config
from typing import Optional, Dict, Any, List
import logging
from threading import Thread
import queue
import requests
import json
import urllib.parse

# Plugin metadata
plugin_name = "Ravencolonial"
plugin_version = "1.2.0"

# Setup logging
logger = logging.getLogger(f"{plugin_name}.{__name__}")

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
        self.is_docked: bool = False
        self.is_construction_ship: bool = False
        
        # Queue for async API calls
        self.api_queue = queue.Queue()
        self.worker_thread = Thread(target=self._api_worker, daemon=True)
        self.worker_thread.start()
        
        # UI elements
        self.status_label: Optional[tk.Label] = None
        self.frame: Optional[tk.Frame] = None
        self.create_button: Optional[tk.Button] = None
        
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
        """Submit cargo contribution to Ravencolonial"""
        try:
            url = f"{self.api_base}/api/project/{build_id}/contribute/{cmdr}"
            response = self.session.post(url, json=cargo_diff, timeout=10)
            response.raise_for_status()
            logger.info(f"Contributed cargo to project {build_id}: {cargo_diff}")
            return True
        except Exception as e:
            logger.error(f"Failed to contribute cargo: {e}")
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
        try:
            url = f"{self.api_base}/api/v2/system/{urllib.parse.quote(system_name)}/sites"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get system sites: {e}")
            return []
    
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
        
        # Check if this is a construction depot delivery
        mission_id = entry.get('MissionID')
        cargo_type = entry.get('Type', '').replace('_name', '')
        count = entry.get('Count', 0)
        
        # Get current project
        project = self.get_project(self.current_system_address, self.current_market_id)
        if not project:
            logger.debug("No project found for current location")
            return
        
        build_id = project.get('buildId')
        if not build_id:
            return
        
        # Queue the contribution
        if entry.get('SubType') == 'Deliver':
            cargo_diff = {cargo_type: count}
            self.queue_api_call(self.contribute_cargo, build_id, self.cmdr_name, cargo_diff)
            self.update_status(f"Delivered {count}x {cargo_type}")
    
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
        """Enable/disable create button based on docking status"""
        if self.create_button:
            if self.is_docked and self.current_market_id and self.is_construction_ship:
                self.create_button['state'] = tk.NORMAL
                self.create_button['text'] = "🚧 Create Project"
            else:
                self.create_button['state'] = tk.DISABLED
                if not self.is_docked:
                    self.create_button['text'] = "Create Project (Dock First)"
                elif not self.is_construction_ship:
                    self.create_button['text'] = "Create Project (Need Construction Ship)"
                else:
                    self.create_button['text'] = "Create Project"


class CreateProjectDialog:
    """Dialog for creating a new colonization project"""
    
    def __init__(self, parent, plugin: RavencolonialPlugin):
        self.plugin = plugin
        self.result = None
        
        # Create top-level window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Create Colonization Project")
        self.dialog.geometry("550x650")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Fetch available system sites
        self.system_sites = []
        if plugin.current_system:
            self.system_sites = plugin.get_system_sites(plugin.current_system)
        
        self._create_widgets()
        self._populate_fields()
        
    def _create_widgets(self):
        """Create dialog widgets"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        row = 0
        
        # Title
        ttk.Label(main_frame, text="New Colonization Project", 
                 font=('TkDefaultFont', 12, 'bold')).grid(row=row, column=0, columnspan=2, pady=(0, 10))
        row += 1
        
        # Location info (read-only)
        ttk.Label(main_frame, text="System:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.system_label = ttk.Label(main_frame, text=self.plugin.current_system or "Unknown")
        self.system_label.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        ttk.Label(main_frame, text="Station:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.station_label = ttk.Label(main_frame, text=self.plugin.current_station or "Unknown")
        self.station_label.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, 
                                                             sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        # Build Type
        ttk.Label(main_frame, text="Build Type:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.build_type_var = tk.StringVar()
        self.build_type_combo = ttk.Combobox(main_frame, textvariable=self.build_type_var, 
                                            state='readonly', width=40)
        # Map display names to API build type codes - organized like SRVSurvey
        self.build_type_map = {
            # Tier 3 Starports
            "Ocellus Starport": "ocellus",
            "Orbis Starport": "apollo",
            "Coriolis Starport": "no_truss",
            "Asteroid Base": "asteroid",
            # Tier 1 Outposts
            "Civilian Outpost": "vesta",
            "Commercial Outpost": "plutus",
            "Industrial Outpost": "vulcan",
            "Military Outpost": "nemesis",
            "Scientific Outpost": "prometheus",
            "Pirate Outpost": "dysnomia",
            # Tier 2 Installations
            "Agricultural Installation": "demeter",
            "Government Installation": "harmonia",
            "Industrial Installation": "euthenia",
            "Medical Installation": "asclepius",
            "Military Installation": "vacuna",
            "Pirate Installation": "apate",
            "Relay Installation": "enodia",
            "Scientific Installation": "astraeus",
            "Security Installation": "dicaeosyne",
            "Space Bar": "dionysus",
            "Tourist Installation": "hedone",
            # Tier 1 Small Installations
            "Comms Installation": "pistis",
            "Satellite Installation": "hermes",
            # Tier 1 Surface Settlements
            "Civilian Settlement": "hestia",
            "Industrial Settlement": "hephaestus",
        }
        self.build_type_combo['values'] = list(self.build_type_map.keys())
        self.build_type_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Project Name
        ttk.Label(main_frame, text="Project Name:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=42)
        self.name_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Architect Name
        ttk.Label(main_frame, text="Architect:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.architect_var = tk.StringVar(value=self.plugin.cmdr_name or "")
        self.architect_entry = ttk.Entry(main_frame, textvariable=self.architect_var, width=42)
        self.architect_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Pre-planned Site Selection (if available)
        if self.system_sites:
            ttk.Label(main_frame, text="Pre-planned Site:").grid(row=row, column=0, sticky=tk.W, pady=2)
            self.site_var = tk.StringVar()
            self.site_combo = ttk.Combobox(main_frame, textvariable=self.site_var, 
                                          state='readonly', width=40)
            site_options = ["<None - Create New>"]
            self.site_id_map = {"<None - Create New>": None}
            for site in self.system_sites:
                site_name = site.get('name', 'Unknown')
                site_type = site.get('buildType', '')
                display_name = f"{site_name} ({site_type})"
                site_options.append(display_name)
                self.site_id_map[display_name] = site.get('id')
            self.site_combo['values'] = site_options
            self.site_combo.current(0)
            self.site_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
            row += 1
        
        # Primary Port checkbox
        self.is_primary_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text="This is the primary port in the system",
                       variable=self.is_primary_var).grid(row=row, column=0, columnspan=2, 
                                                          sticky=tk.W, pady=5)
        row += 1
        
        # Notes
        ttk.Label(main_frame, text="Notes:").grid(row=row, column=0, sticky=(tk.W, tk.N), pady=2)
        self.notes_text = tk.Text(main_frame, width=40, height=6)
        self.notes_text.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Discord Link
        ttk.Label(main_frame, text="Discord Link:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.discord_var = tk.StringVar()
        self.discord_entry = ttk.Entry(main_frame, textvariable=self.discord_var, width=42)
        self.discord_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Create", command=self._on_create).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.LEFT, padx=5)
        
    def _populate_fields(self):
        """Auto-populate fields from current game state"""
        if self.plugin.current_station and self.plugin.current_system:
            suggested_name = f"{self.plugin.current_system} - {self.plugin.current_station}"
            self.name_var.set(suggested_name)
    
    def _on_create(self):
        """Handle create button click"""
        # Validate inputs
        if not self.build_type_var.get():
            messagebox.showerror("Error", "Please select a build type")
            return
        
        if not self.name_var.get():
            messagebox.showerror("Error", "Please enter a project name")
            return
        
        # Prepare project data matching RavenColonial API schema
        build_type_display = self.build_type_var.get()
        build_type_api = self.build_type_map.get(build_type_display)
        
        if not build_type_api:
            messagebox.showerror("Error", "Invalid build type selected")
            return
        
        project_data = {
            "buildType": build_type_api,
            "buildName": self.name_var.get(),
            "marketId": int(self.plugin.current_market_id),
            "systemAddress": int(self.plugin.current_system_address),
            "systemName": self.plugin.current_system,
            "starPos": self.plugin.star_pos or [0.0, 0.0, 0.0],
            "isPrimaryPort": self.is_primary_var.get(),
            "commodities": {},  # Required field - server will populate from build type
        }
        
        # Architect name (optional in API but good to include)
        arch_name = self.architect_var.get() or self.plugin.cmdr_name
        if arch_name:
            project_data["architectName"] = arch_name
        
        # Optional fields
        notes = self.notes_text.get("1.0", tk.END).strip()
        if notes:
            project_data["notes"] = notes
            
        if self.plugin.body_num:
            project_data["bodyNum"] = int(self.plugin.body_num)
        if self.plugin.body_name:
            project_data["bodyName"] = self.plugin.body_name
        if self.discord_var.get():
            project_data["discordLink"] = self.discord_var.get()
        
        # Add pre-planned site ID if selected
        if self.system_sites and hasattr(self, 'site_var'):
            selected_site = self.site_var.get()
            site_id = self.site_id_map.get(selected_site)
            if site_id:
                project_data["systemSiteId"] = site_id
        
        # Create project
        logger.info("User clicked Create - sending project to API")
        result = self.plugin.create_project(project_data)
        
        if result:
            build_id = result.get('buildId')
            messagebox.showinfo("Success", 
                              f"Project created successfully!\n\nBuild ID: {build_id}")
            # Open project page in browser
            if build_id:
                open_url(f"https://ravencolonial.com/#build={build_id}")
            self.result = result
            self.dialog.destroy()
        else:
            error_msg = (
                "Failed to create project.\n\n"
                f"API URL: {self.plugin.api_base}/api/project/\n\n"
                "Check EDMC logs for detailed error message:\n"
                "%TEMP%\\EDMarketConnector\\EDMarketConnector.log\n\n"
                "Common issues:\n"
                "- Invalid build type\n"
                "- Missing required fields\n"
                "- API connectivity problems"
            )
            messagebox.showerror("Error", error_msg)
    
    def _on_cancel(self):
        """Handle cancel button click"""
        self.dialog.destroy()


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
        logger.info(f"{plugin_name} stopped")


def plugin_prefs(parent: nb.Notebook, cmdr: str, is_beta: bool) -> Optional[tk.Frame]:
    """
    Create a preferences frame for the plugin.
    
    :param parent: The parent notebook
    :param cmdr: Current commander name
    :param is_beta: Whether game is in beta
    :return: A tk.Frame for the settings
    """
    frame = nb.Frame(parent)
    frame.columnconfigure(1, weight=1)
    
    # Title
    nb.Label(frame, text="Ravencolonial Colonization Tracker").grid(
        row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10)
    )
    
    # Info text
    info_text = (
        "This plugin automatically tracks colonization deliveries and sends\n"
        "data to ravencolonial.com. No additional configuration needed!"
    )
    nb.Label(frame, text=info_text, justify=tk.LEFT).grid(
        row=1, column=0, columnspan=2, sticky=tk.W
    )
    
    # Link to ravencolonial.com
    nb.Label(frame, text="Website:").grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
    link = nb.Label(frame, text="ravencolonial.com", foreground="blue", cursor="hand2")
    link.grid(row=2, column=1, sticky=tk.W, pady=(10, 0))
    link.bind("<Button-1>", lambda e: open_url("https://ravencolonial.com"))
    
    return frame


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    """
    Handle preference changes.
    
    :param cmdr: Current commander name
    :param is_beta: Whether game is in beta
    """
    pass


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
    this.status_label = tk.Label(frame, text="Ravencolonial: Ready")
    this.status_label.pack(side=tk.LEFT, padx=5)
    
    # Create project button
    this.create_button = tk.Button(
        frame, 
        text="Create Project (Dock First)",
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
    
    event = entry.get('event')
    
    # Handle different events
    if event == 'Docked':
        this.current_market_id = entry.get('MarketID')
        this.current_system_address = entry.get('SystemAddress')
        this.star_pos = entry.get('StarPos')
        this.body_num = entry.get('BodyID')
        this.body_name = entry.get('Body')
        this.station_type = entry.get('StationType')
        this.faction_name = entry.get('StationFaction', {}).get('Name')
        this.is_docked = True
        # Check if this is a construction ship
        station_name = entry.get('StationName', '').lower()
        this.is_construction_ship = 'construction' in station_name
        this.update_status(f"Docked at {station}")
        this.update_create_button()
        
    elif event == 'Undocked':
        this.is_docked = False
        this.is_construction_ship = False
        this.current_market_id = None
        this.update_status(f"Undocked from {station}")
        this.update_create_button()
        
    elif event == 'Location':
        this.current_system_address = entry.get('SystemAddress')
        this.star_pos = entry.get('StarPos')
        if entry.get('Docked'):
            this.current_market_id = entry.get('MarketID')
            this.body_num = entry.get('BodyID')
            this.body_name = entry.get('Body')
            this.station_type = entry.get('StationType')
            this.is_docked = True
            # Check if this is a construction ship
            station_name = entry.get('StationName', '').lower()
            this.is_construction_ship = 'construction' in station_name
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
    
    return None


def open_url(url: str):
    """Open URL in browser"""
    import webbrowser
    webbrowser.open(url)


def open_create_dialog(parent):
    """Open the Create Project dialog"""
    global this
    if this:
        try:
            dialog = CreateProjectDialog(parent, this)
        except Exception as e:
            logger.error(f"Failed to open create dialog: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to open dialog: {str(e)}")
