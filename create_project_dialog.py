"""
Dialog for creating new Ravencolonial colonization projects.

This module handles the UI and logic for creating new colonization tracking projects
when docked at a construction ship.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import webbrowser
import json
from typing import Optional, Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from load import RavencolonialPlugin

# Get logger
logger = logging.getLogger(__name__)

# Localization helper (will be set by load.py)
plugin_tl = None


def set_translation_function(tl_func):
    """Set the translation function from the main plugin"""
    global plugin_tl
    plugin_tl = tl_func


def open_url(url: str):
    """Open URL in browser"""
    webbrowser.open(url)


class CreateProjectDialog:
    """Dialog for creating a new colonization project"""
    
    def __init__(self, parent, plugin: 'RavencolonialPlugin'):
        self.plugin = plugin
        self.result = None
        
        # Create top-level window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Create Colonization Project")
        self.dialog.geometry("550x650")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Fetch available system sites and bodies
        self.system_sites = []
        self.system_bodies = []
        logger.debug(f"Dialog initialization - current_system: {plugin.current_system}")
        if plugin.current_system:
            logger.debug(f"Fetching system sites for: {plugin.current_system}")
            self.system_sites = plugin.get_system_sites(plugin.current_system)
            
            # Filter out completed and build sites
            original_count = len(self.system_sites)
            self.system_sites = [site for site in self.system_sites if site.get('status') not in ('complete', 'build')]
            filtered_count = original_count - len(self.system_sites)
            if filtered_count > 0:
                logger.debug(f"Filtered out {filtered_count} completed/build sites")
            
            logger.debug(f"Fetched {len(self.system_sites)} system sites")
            if self.system_sites:
                logger.debug(f"Sample site data: {self.system_sites[0]}")
            else:
                logger.debug("No system sites returned - API may be empty or failed")
        else:
            logger.debug("No current_system available - cannot fetch system sites")
        
        # Get system address - try from plugin state first, then from journal
        system_address = plugin.current_system_address
        if not system_address:
            logger.debug("No system_address in plugin state, checking journal")
            system_address = plugin.get_system_address_from_journal()
            if system_address:
                logger.debug(f"Got system_address from journal: {system_address}")
                # Store it for future use
                plugin.current_system_address = system_address
        
        # Fetch bodies from Ravencolonial using system address
        if system_address:
            logger.debug(f"Fetching bodies from Ravencolonial for system address: {system_address}")
            self.system_bodies = plugin.get_system_bodies(system_address)
            logger.debug(f"Received {len(self.system_bodies)} bodies from Ravencolonial")
        else:
            logger.debug("No system address available, cannot fetch bodies")
        
        # Combine data from both APIs
        self.available_bodies = {}  # Map of bodyNum to body info
        self._combine_body_data()
        
        self._create_widgets()
        self._populate_fields()
        
    def _combine_body_data(self):
        """Combine body data from both /bodies and /sites APIs"""
        logger.debug("Combining body data from bodies and sites APIs")
        
        # First, get all bodies from the /bodies API with their names
        bodies_by_num = {}
        for body in self.system_bodies:
            # Note: Must check explicitly for None, not use 'or' chain, because 0 is falsy
            body_num = body.get('id')
            if body_num is None:
                body_num = body.get('num')
            if body_num is None:
                body_num = body.get('bodyId')
            body_name = body.get('name', '')
            body_type = body.get('type', '')
            
            if body_num is not None:
                body_num_str = str(body_num)
                bodies_by_num[body_num_str] = {
                    'name': body_name,
                    'type': body_type,
                    'num': body_num
                }
                logger.debug(f"Body from /bodies API: {body_num_str} = {body_name} ({body_type})")
        
        # Then, add bodies that have pre-planned sites from /sites API
        site_bodies = set()
        for site in self.system_sites:
            # Try different possible field names for bodyNum
            # Note: Must check explicitly for None, not use 'or' chain, because 0 is falsy
            body_num = site.get('bodyNum')
            if body_num is None:
                body_num = site.get('body_id')
            if body_num is None:
                body_num = site.get('bodyId')
            if body_num is None:
                body_num = site.get('body_num')
            
            if body_num is not None:
                body_num_str = str(body_num)
                site_bodies.add(body_num_str)
                logger.debug(f"Body from /sites API: {body_num_str}")
        
        # Combine: Always show all bodies from the bodies API
        # (Pre-planned sites are just for auto-population, not filtering)
        self.available_bodies = bodies_by_num.copy()
        logger.debug(f"Using all {len(bodies_by_num)} bodies from bodies API")
        
        # Also add any bodies from sites API that aren't in bodies API
        if site_bodies:
            for body_num_str in site_bodies:
                if body_num_str not in self.available_bodies:
                    # Body has site but not in bodies API, add with generic name
                    self.available_bodies[body_num_str] = {
                        'name': f'Body {body_num_str}',
                        'type': 'Unknown',
                        'num': int(body_num_str)
                    }
                    logger.debug(f"Added body with site (not in bodies API): {body_num_str}")
        
        logger.debug(f"Combined data: {len(self.available_bodies)} unique bodies available")
    
    def _create_widgets(self):
        """Create dialog widgets"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        row = 0
        
        # Title
        ttk.Label(main_frame, text=plugin_tl("New Colonization Project"), 
                 font=('TkDefaultFont', 12, 'bold')).grid(row=row, column=0, columnspan=2, pady=(0, 10))
        row += 1
        
        # Location info (read-only)
        ttk.Label(main_frame, text=plugin_tl("System:")).grid(row=row, column=0, sticky=tk.W, pady=2)
        self.system_label = ttk.Label(main_frame, text=self.plugin.current_system or plugin_tl("Unknown"))
        self.system_label.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        ttk.Label(main_frame, text=plugin_tl("Station:")).grid(row=row, column=0, sticky=tk.W, pady=2)
        self.station_label = ttk.Label(main_frame, text=self.plugin.current_station or plugin_tl("Unknown"))
        self.station_label.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1
        
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, 
                                                             sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        # Construction Type (two-dropdown system like SRVSurvey)
        # Hierarchical structure: Tier/Category -> Model -> API Code
        self.construction_types = {
            # Tier 3 Starports
            "Tier 3: Ocellus Starport": {"Ocellus": "ocellus"},
            "Tier 3: Orbis Starport": {
                "Apollo": "apollo",
                "Artemis": "artemis"
            },
            "Tier 3: Large Planetary Port": {
                "Aphrodite": "aphrodite",
                "Hera": "hera",
                "Poseidon": "poseidon",
                "Zeus": "zeus"
            },
            # Tier 2 Starports
            "Tier 2: Coriolis Starport": {
                "No truss": "no_truss",
                "Dual truss": "dual_truss",
                "Quad truss": "quad_truss"
            },
            "Tier 2: Asteroid Starport": {"Asteroid": "asteroid"},
            # Tier 1 Outposts
            "Tier 1: Civilian Outpost": {"Vesta": "vesta"},
            "Tier 1: Commercial Outpost": {"Plutus": "plutus"},
            "Tier 1: Industrial Outpost": {"Vulcan": "vulcan"},
            "Tier 1: Military Outpost": {"Nemesis": "nemesis"},
            "Tier 1: Scientific Outpost": {"Prometheus": "prometheus"},
            "Tier 1: Pirate Outpost": {"Dysnomia": "dysnomia"},
            # Tier 1 Small Installations
            "Tier 1: Satellite Installation": {
                "Angelia": "angelia",
                "Eirene": "eirene",
                "Hermes": "hermes"
            },
            "Tier 1: Communication Installation": {
                "Aletheia": "aletheia",
                "Pistis": "pistis",
                "Soter": "soter"
            },
            "Tier 1: Space Farm": {"Demeter": "demeter"},
            "Tier 1: Pirate Base Installation": {
                "Apate": "apate",
                "Laverna": "laverna"
            },
            "Tier 1: Mining/Industrial Installation": {
                "Euthenia": "euthenia",
                "Phorcys": "phorcys"
            },
            "Tier 1: Relay Installation": {
                "Enodia": "enodia",
                "Ichnaea": "ichnaea"
            },
            # Tier 1 Surface Outposts
            "Tier 1: Civilian Surface Outpost": {
                "Atropos": "atropos",
                "Clotho": "clotho",
                "Decima": "decima",
                "Hestia": "hestia",
                "Lachesis": "lachesis",
                "Nona": "nona"
            },
            "Tier 1: Industrial Surface Outpost": {
                "Bia": "bia",
                "Hephaestus": "hephaestus",
                "Mefitis": "mefitis",
                "Opis": "opis",
                "Ponos": "ponos",
                "Tethys": "tethys"
            },
            "Tier 1: Scientific Surface Outpost": {
                "Ananke": "ananke",
                "Antevorta": "antevorta",
                "Fauna": "fauna",
                "Necessitas": "necessitas",
                "Porrima": "porrima",
                "Providentia": "providentia"
            },
            # Tier 1 Settlements
            "Tier 1: Agriculture Settlement: Small": {"Consus": "consus"},
            "Tier 1: Agriculture Settlement: Medium": {
                "Annona": "annona",
                "Picumnus": "picumnus"
            },
            "Tier 1: Mining Settlement: Small": {"Ourea": "ourea"},
            "Tier 1: Mining Settlement: Medium": {
                "Mantus": "mantus",
                "Orcus": "orcus"
            },
            "Tier 1: Industrial Settlement: Small": {"Fontus": "fontus"},
            "Tier 1: Industrial Settlement: Medium": {
                "Meteope": "meteope",
                "Minthe": "minthe",
                "Palici": "palici"
            },
            "Tier 1: Military Settlement: Small": {"Ioke": "ioke"},
            "Tier 1: Military Settlement: Medium": {
                "Bellona": "bellona",
                "Enyo": "enyo",
                "Polemos": "polemos"
            },
            # Tier 2 Installations
            "Tier 2: Military Installation": {
                "Alastor": "alastor",
                "Vacuna": "vacuna"
            },
            "Tier 2: Security Installation": {
                "Dicaeosyne": "dicaeosyne",
                "Eunomia": "eunomia",
                "Nomos": "nomos",
                "Poena": "poena"
            },
            "Tier 2: Government Installation": {"Harmonia": "harmonia"},
            "Tier 2: Medical Installation": {
                "Asclepius": "asclepius",
                "Eupraxia": "eupraxia"
            },
            "Tier 2: Research Installation": {
                "Astraeus": "astraeus",
                "Coeus": "coeus",
                "Dione": "dione",
                "Dodona": "dodona"
            },
            "Tier 2: Tourist Installation": {
                "Hedone": "hedone",
                "Opora": "opora",
                "Pasithea": "pasithea"
            },
            "Tier 2: Space Bar Installation": {
                "Bacchus": "bacchus",
                "Dionysus": "dionysus"
            },
            # Tier 2 Settlements
            "Tier 2: Agriculture Settlement: Large": {
                "Ceres": "ceres",
                "Fornax": "fornax"
            },
            "Tier 2: Mining Settlement: Large": {
                "Aerecura": "aerecura",
                "Erebus": "erebus"
            },
            "Tier 2: Military Settlement: Large": {"Gaea": "gaea"},
            "Tier 2: Industrial Settlement: Large": {"Minerva": "minerva"},
            "Tier 2: Bio Settlement: Small": {"Phoebe": "phoebe"},
            "Tier 2: Bio Settlement: Medium": {
                "Asteria": "asteria",
                "Caerus": "caerus"
            },
            "Tier 2: Bio Settlement: Large": {"Chronos": "chronos"},
            "Tier 2: Tourist Settlement: Small": {"Aergia": "aergia"},
            "Tier 2: Tourist Settlement: Medium": {
                "Comus": "comus",
                "Gelos": "gelos"
            },
            "Tier 2: Tourist Settlement: Large": {"Fufluns": "fufluns"},
            # Tier 2 Hubs
            "Tier 2: Extraction Hub": {"Tartarus": "tartarus"},
            "Tier 2: Civilian Hub": {"Aegle": "aegle"},
            "Tier 2: Exploration Hub": {"Tellus": "tellus"},
            "Tier 2: Outpost Hub": {"Io": "io"},
            "Tier 2: Scientific Hub": {
                "Athena": "athena",
                "Caelus": "caelus"
            },
            "Tier 2: Military Hub": {
                "Alala": "alala",
                "Ares": "ares"
            },
            "Tier 2: Refinery Hub": {
                "Silenus": "silenus"
            },
            "Tier 2: High Tech Hub": {"Janus": "janus"},
            "Tier 2: Industrial Hub": {
                "Eunostus": "eunostus",
                "Molae": "molae",
                "Tellus": "tellus"
            },
        }
        
        # First dropdown: Construction Type (Tier + Category)
        ttk.Label(main_frame, text=plugin_tl("Construction Type:")).grid(row=row, column=0, sticky=tk.W, pady=2)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(main_frame, textvariable=self.category_var, 
                                          state='readonly', width=40)
        self.category_combo['values'] = list(self.construction_types.keys())
        self.category_combo.bind('<<ComboboxSelected>>', self._on_category_selected)
        self.category_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Second dropdown: Model/Variant
        ttk.Label(main_frame, text=plugin_tl("Model:")).grid(row=row, column=0, sticky=tk.W, pady=2)
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(main_frame, textvariable=self.model_var, 
                                       state='readonly', width=40)
        self.model_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Project Name
        ttk.Label(main_frame, text=plugin_tl("Project Name:")).grid(row=row, column=0, sticky=tk.W, pady=2)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=42)
        self.name_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Body Selection (populated from combined bodies/sites data)
        ttk.Label(main_frame, text=plugin_tl("Body:")).grid(row=row, column=0, sticky=tk.W, pady=2)
        self.body_var = tk.StringVar()
        self.body_combo = ttk.Combobox(main_frame, textvariable=self.body_var, width=40)
        # Populate with bodies from combined data
        body_options = []
        logger.debug(f"Creating body dropdown from {len(self.available_bodies)} combined bodies")
        
        for body_num, body_info in self.available_bodies.items():
            body_name = body_info.get('name', f'Body {body_num}')
            body_type = body_info.get('type', '')
            # Display format: "Body Name (Body Type) [ID: 123]" to show both name and bodyNum
            if body_type:
                display_name = f"{body_name} ({body_type}) [ID: {body_num}]"
            else:
                display_name = f"{body_name} [ID: {body_num}]"
            body_options.append(display_name)
            logger.debug(f"Added body option: {display_name}")
        
        # Sort options by body name for better UX
        body_options.sort(key=lambda x: x.split(' [ID:')[0])
        
        if body_options:
            self.body_combo['values'] = body_options
            logger.debug(f"Body dropdown populated with {len(body_options)} options from combined data")
            # Pre-select current body if available
            if self.plugin.body_num and str(self.plugin.body_num) in self.available_bodies:
                current_body_info = self.available_bodies[str(self.plugin.body_num)]
                current_body_name = current_body_info.get('name', f'Body {self.plugin.body_num}')
                current_body_type = current_body_info.get('type', '')
                if current_body_type:
                    display_name = f"{current_body_name} ({current_body_type}) [ID: {self.plugin.body_num}]"
                else:
                    display_name = f"{current_body_name} [ID: {self.plugin.body_num}]"
                if display_name in body_options:
                    self.body_var.set(display_name)
                    logger.debug(f"Pre-selected current body: {display_name}")
                else:
                    self.body_var.set(body_options[0])
                    logger.debug(f"Pre-selected first body (current not found): {body_options[0]}")
            else:
                self.body_var.set(body_options[0])
                logger.debug(f"Pre-selected first body: {body_options[0]}")
        else:
            logger.warning("No body options available from combined data")
        
        self.body_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Architect Name
        ttk.Label(main_frame, text=plugin_tl("Architect:")).grid(row=row, column=0, sticky=tk.W, pady=2)
        
        # Try to get architect from system API, otherwise use CMDR name
        architect_name = self.plugin.cmdr_name or ""
        if self.plugin.current_system_address:
            system_architect = self.plugin.get_system_architect(self.plugin.current_system_address)
            if system_architect:
                architect_name = system_architect
                logger.info(f"Found system architect: {system_architect}")
        
        self.architect_var = tk.StringVar(value=architect_name)
        self.architect_entry = ttk.Entry(main_frame, textvariable=self.architect_var, width=42)
        self.architect_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Pre-planned Site Selection (if available)
        if self.system_sites:
            ttk.Label(main_frame, text=plugin_tl("Pre-planned Site:")).grid(row=row, column=0, sticky=tk.W, pady=2)
            self.site_var = tk.StringVar()
            self.site_combo = ttk.Combobox(main_frame, textvariable=self.site_var, 
                                          state='readonly', width=40)
            site_options = [plugin_tl("<None - Create New>")]
            self.site_id_map = {plugin_tl("<None - Create New>"): None}
            self.site_data_map = {"<None - Create New>": None}  # Store full site data
            for site in self.system_sites:
                site_name = site.get('name', 'Unknown')
                site_type = site.get('buildType', '')
                display_name = f"{site_name} ({site_type})"
                site_options.append(display_name)
                self.site_id_map[display_name] = site.get('id')
                self.site_data_map[display_name] = site  # Store complete site data
            self.site_combo['values'] = site_options
            self.site_combo.current(0)
            self.site_combo.bind('<<ComboboxSelected>>', self._on_site_selected)
            self.site_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
            row += 1
        
        # Notes
        ttk.Label(main_frame, text=plugin_tl("Notes:")).grid(row=row, column=0, sticky=(tk.W, tk.N), pady=2)
        self.notes_text = tk.Text(main_frame, width=40, height=6)
        self.notes_text.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Discord Link
        ttk.Label(main_frame, text=plugin_tl("Discord Link:")).grid(row=row, column=0, sticky=tk.W, pady=2)
        self.discord_var = tk.StringVar()
        self.discord_entry = ttk.Entry(main_frame, textvariable=self.discord_var, width=42)
        self.discord_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        row += 1
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text=plugin_tl("Create"), command=self._on_create).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=plugin_tl("Cancel"), command=self._on_cancel).pack(side=tk.LEFT, padx=5)
        
    def _on_category_selected(self, event=None):
        """Handle category selection - populate model dropdown"""
        category = self.category_var.get()
        if category and category in self.construction_types:
            models = list(self.construction_types[category].keys())
            self.model_combo['values'] = models
            if models:
                self.model_var.set(models[0])  # Auto-select first model
        else:
            self.model_combo['values'] = []
            self.model_var.set('')
    
    def _on_site_selected(self, event=None):
        """Handle pre-planned site selection - auto-populate construction type, model, and body"""
        selected_display = self.site_var.get()
        
        # If "<None - Create New>" is selected, clear the fields
        if selected_display == "<None - Create New>":
            return
        
        # Get the site data
        site_data = self.site_data_map.get(selected_display)
        if not site_data:
            return
        
        build_type = site_data.get('buildType', '')
        logger.debug(f"Site selected with buildType: {build_type}")
        logger.debug(f"Full site data: {site_data}")
        
        # Search through construction_types to find matching category and model
        for category, models in self.construction_types.items():
            for model_name, model_value in models.items():
                if model_value == build_type:
                    logger.debug(f"Found match: category={category}, model={model_name}")
                    
                    # Set the category
                    self.category_var.set(category)
                    
                    # Populate models for this category
                    model_list = list(self.construction_types[category].keys())
                    self.model_combo['values'] = model_list
                    
                    # Set the specific model
                    self.model_var.set(model_name)
                    
                    # Set the body if available in site data
                    self._set_body_from_site(site_data)
                    return
        
        logger.warning(f"No matching construction type found for buildType: {build_type}")
    
    def _set_body_from_site(self, site_data):
        """Set the body dropdown based on site data"""
        # Show all available fields in site data for debugging
        logger.debug(f"Site data available fields: {list(site_data.keys())}")
        
        # Try to get bodyNum from the site (this is what Ravencolonial uses)
        # Note: Must check explicitly for None, not use 'or' chain, because 0 is falsy
        site_body_num = site_data.get('bodyNum')
        if site_body_num is None:
            site_body_num = site_data.get('body_id')
        if site_body_num is None:
            site_body_num = site_data.get('bodyId')
        if site_body_num is None:
            site_body_num = site_data.get('body_num')
        
        logger.debug(f"Site bodyNum: {site_body_num} (type: {type(site_body_num)})")
        
        if site_body_num is None:
            logger.debug("No bodyNum found in site data, checking all fields...")
            # Log all fields that might contain body information
            for key, value in site_data.items():
                if 'body' in key.lower():
                    logger.debug(f"Potential body field '{key}': {value}")
            return
        
        # Search through body options to find matching body by bodyNum
        body_options = list(self.body_combo['values'])
        logger.debug(f"Available body options: {body_options}")
        
        # Look for the body with matching bodyNum using new format [ID: 123]
        # Convert to string to ensure consistent comparison
        target_display = f"[ID: {str(site_body_num)}]"
        logger.debug(f"Searching for target: '{target_display}'")
        
        for body_option in body_options:
            if body_option and target_display in body_option:
                logger.debug(f"Found matching body by bodyNum: '{body_option}'")
                self.body_var.set(body_option)
                logger.info(f"Successfully set body to: '{body_option}'")
                return
        
        logger.warning(f"Could not find matching body for site bodyNum: {site_body_num}")
        logger.warning(f"Target was: '{target_display}'")
    
    def _populate_fields(self):
        """Auto-populate fields from current game state"""
        if self.plugin.current_station:
            # Clean up station name - remove localization tokens like "$EXT_PANEL_ColonisationShip; "
            station_name = self.plugin.current_station
            if ';' in station_name:
                # Extract the part after the semicolon (the actual name)
                station_name = station_name.split(';', 1)[1].strip()
            
            # Trim construction site prefixes
            if station_name.startswith('Planetary Construction Site: '):
                station_name = station_name[len('Planetary Construction Site: '):]
            elif station_name.startswith('Orbital Construction Site: '):
                station_name = station_name[len('Orbital Construction Site: '):]
            
            # Use only the station name, not the system
            self.name_var.set(station_name)
    
    def _on_create(self):
        """Handle create button click"""
        # Validate inputs
        if not self.category_var.get():
            messagebox.showerror(plugin_tl("Error"), plugin_tl("Please select a construction type"))
            return
        
        if not self.model_var.get():
            messagebox.showerror(plugin_tl("Error"), plugin_tl("Please select a model"))
            return
        
        if not self.name_var.get():
            messagebox.showerror(plugin_tl("Error"), plugin_tl("Please enter a project name"))
            return
        
        # Validate required plugin data
        if not self.plugin.current_market_id:
            messagebox.showerror(plugin_tl("Error"), plugin_tl("Market ID not available. Please re-dock at the construction ship."))
            return
        
        if not self.plugin.current_system:
            messagebox.showerror(plugin_tl("Error"), plugin_tl("System name not available. Please re-dock or restart EDMC while in-game."))
            return
        
        # Validate system address
        if not self.plugin.current_system_address:
            logger.debug("System address missing, attempting to fetch from journal")
            self.plugin.current_system_address = self.plugin.get_system_address_from_journal()
            
            if not self.plugin.current_system_address:
                messagebox.showerror(plugin_tl("Error"), plugin_tl("System address not available. Please re-dock or restart EDMC while in-game."))
                return
        
        # Get build type API code from category + model selection
        category = self.category_var.get()
        model = self.model_var.get()
        build_type_api = self.construction_types.get(category, {}).get(model)
        
        if not build_type_api:
            messagebox.showerror(plugin_tl("Error"), plugin_tl("Invalid construction type/model selected"))
            return
        
        # Extract commodities from construction depot data
        commodities = {}
        supply_commodities = {}  # For supply update - remaining need
        max_need = 0
        if self.plugin.construction_depot_data:
            resources = self.plugin.construction_depot_data.get('ResourcesRequired', [])
            for resource in resources:
                # Remove the _name suffix and $ prefix from commodity names
                commodity_name = resource.get('Name', '').replace('$', '').replace('_name;', '').lower()
                required_amount = resource.get('RequiredAmount', 0)
                provided_amount = resource.get('ProvidedAmount', 0)
                
                if commodity_name and required_amount > 0:
                    # For project creation: send required amount
                    commodities[commodity_name] = required_amount
                    max_need += required_amount
                    
                    # For supply update: calculate remaining need
                    remaining_need = required_amount - provided_amount
                    if remaining_need > 0:
                        supply_commodities[commodity_name] = remaining_need
                        logger.debug(f"Supply update: {commodity_name} needs {remaining_need} more ({required_amount} - {provided_amount})")
                    else:
                        logger.debug(f"Supply update: {commodity_name} already satisfied ({required_amount} - {provided_amount})")
        else:
            logger.warning("No construction depot data available - commodities list will be empty")
        
        # Architect name
        arch_name = self.architect_var.get() or self.plugin.cmdr_name or "Unknown"
        
        project_data = {
            "buildType": build_type_api,
            "buildName": self.name_var.get(),
            "marketId": int(self.plugin.current_market_id),
            "systemAddress": int(self.plugin.current_system_address),
            "systemName": self.plugin.current_system,
            "starPos": self.plugin.star_pos or [0.0, 0.0, 0.0],
            "commodities": commodities,
            "maxNeed": max_need,
            "architectName": arch_name,
            "commanders": {arch_name: []},
        }
        
        # Optional fields
        notes = self.notes_text.get("1.0", tk.END).strip()
        if notes:
            project_data["notes"] = notes
        
        # Extract body selection from dropdown
        selected_body_display = self.body_var.get()
        logger.debug(f"Selected body from dropdown: '{selected_body_display}'")
        if selected_body_display:
            # Parse the display name to extract bodyNum and bodyName
            # Format is "Body Name (Body Type) [ID: 123]" or "Body Name [ID: 123]"
            if ' [ID: ' in selected_body_display:
                # Extract body name (everything before [ID:)
                body_part = selected_body_display.split(' [ID:')[0]
                # Extract bodyNum (between [ID: and ])
                body_num_str = selected_body_display.split(' [ID:')[1].rstrip(']')
                
                # Remove body type from name if present (everything in parentheses)
                if ' (' in body_part and ')' in body_part:
                    selected_body_name = body_part.split(' (')[0]
                else:
                    selected_body_name = body_part
                
                try:
                    body_num = int(body_num_str)
                    project_data["bodyNum"] = body_num
                    project_data["bodyName"] = selected_body_name
                    logger.debug(f"Set bodyNum to: {body_num}, bodyName to: '{selected_body_name}'")
                except ValueError:
                    logger.warning(f"Could not parse bodyNum from: '{body_num_str}'")
                    project_data["bodyName"] = selected_body_name
            else:
                # Fallback for unexpected format
                logger.warning(f"Unexpected body format: '{selected_body_display}'")
                project_data["bodyName"] = selected_body_display
        elif self.plugin.body_num:
            # Fallback to plugin data if no selection
            project_data["bodyNum"] = int(self.plugin.body_num)
            if self.plugin.body_name:
                project_data["bodyName"] = self.plugin.body_name
        elif self.plugin.body_name:
            # Fallback to plugin data if no selection
            project_data["bodyName"] = self.plugin.body_name
        
        discord_link = self.discord_var.get()
        if discord_link:
            project_data["discordLink"] = discord_link
        else:
            project_data["discordLink"] = None
        
        # Include the full construction depot event data
        if self.plugin.construction_depot_data:
            project_data["colonisationConstructionDepot"] = self.plugin.construction_depot_data
        
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
            
            # Update project supply with remaining need totals
            if build_id and supply_commodities:
                # Calculate remaining maxNeed (sum of remaining needs)
                remaining_max_need = sum(supply_commodities.values())
                logger.info(f"Updating supply totals for new project {build_id}")
                logger.debug(f"Supply commodities: {supply_commodities}")
                logger.debug(f"Remaining maxNeed: {remaining_max_need}")
                
                supply_payload = {
                    "buildId": build_id,
                    "commodities": supply_commodities,
                    "maxNeed": remaining_max_need
                }
                # Queue the supply update
                self.plugin.queue_api_call(self.plugin.update_project_supply, build_id, supply_payload)
            elif build_id and commodities:
                logger.info(f"Project {build_id} has no remaining supply needs - all commodities satisfied")
            
            # Open project page in browser (no success popup)
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
            messagebox.showerror(plugin_tl("Error"), error_msg)
    
    def _on_cancel(self):
        """Handle cancel button click"""
        self.dialog.destroy()
