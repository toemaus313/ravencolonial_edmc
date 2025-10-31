"""
UI Manager for Ravencolonial EDMC Plugin

Handles UI state management and updates.
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class UIManager:
    """Manages UI elements and state for the Ravencolonial plugin"""
    
    def __init__(self, plugin_instance):
        """
        Initialize the UI manager
        
        :param plugin_instance: The main plugin instance
        """
        self.plugin = plugin_instance
        self.status_label: Optional[tk.Label] = None
        self.create_button: Optional[tk.Button] = None
        self.project_link_label: Optional[tk.Label] = None
    
    def create_plugin_frame(self, parent: tk.Frame) -> tk.Frame:
        """
        Create the main plugin frame for EDMC
        
        :param parent: The parent frame
        :return: The created frame
        """
        frame = tk.Frame(parent)
        self.plugin.frame = frame
        
        # Status label
        self.status_label = tk.Label(frame, text="Ravencolonial: Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)
        self.plugin.status_label = self.status_label
        
        # Project link label (shows when project exists)
        self.project_link_label = tk.Label(frame, text="", cursor="hand2", fg='blue')
        self.project_link_label.pack(side=tk.LEFT, padx=5)
        self.project_link_label.bind("<Button-1>", lambda e: self._open_project_link())
        self.plugin.project_link_label = self.project_link_label
        self.plugin.current_build_id = None
        
        # Create project button
        self.create_button = tk.Button(
            frame, 
            text="Create Project (Dock First)",
            command=lambda: self._open_create_dialog(parent),
            state=tk.DISABLED
        )
        self.create_button.pack(side=tk.LEFT, padx=5)
        self.plugin.create_button = self.create_button
        
        return frame
    
    def update_status(self, message: str):
        """
        Update the UI status label
        
        :param message: The status message to display
        """
        if self.status_label:
            self.status_label['text'] = message
            logger.info(message)
    
    def update_create_button(self):
        """Enable/disable create button based on docking status and existing projects"""
        logger.debug(f"update_create_button - is_docked: {self.plugin.is_docked}, market_id: {self.plugin.current_market_id}, is_construction_ship: {self.plugin.is_construction_ship}")
        
        if not self.create_button:
            return
        
        # Check if we're at a construction ship
        if self.plugin.is_docked and self.plugin.current_market_id and self.plugin.is_construction_ship:
            # Get system address if we don't have it
            if not self.plugin.current_system_address:
                logger.debug("No system_address, fetching from journal for project check")
                self.plugin.current_system_address = self.plugin.get_system_address_from_journal()
            
            # Check for existing project
            if self.plugin.current_system_address:
                existing_project = self.plugin.check_existing_project(self.plugin.current_system_address, self.plugin.current_market_id)
            else:
                logger.warning("Could not get system_address, unable to check for existing project")
                existing_project = None
            
            if existing_project:
                # Project exists - change button to open build page
                build_id = existing_project.get('buildId', '')
                build_name = existing_project.get('buildName', 'Unknown')
                logger.info(f"Found existing project: {build_name} ({build_id})")
                
                self.create_button['state'] = tk.NORMAL
                self.create_button['text'] = "🌐 Open Build Page"
                # Change button command to open project link
                self.create_button['command'] = lambda: self._open_project_link()
                
                if self.project_link_label:
                    link_text = f"{build_name}"
                    self.project_link_label['text'] = link_text
                    self.project_link_label['fg'] = 'blue'
                    self.project_link_label['cursor'] = 'hand2'
                
                # Store build_id for click handler
                self.plugin.current_build_id = build_id
            else:
                # No project exists - fetch body data then enable button
                logger.info("No existing project found")
                
                # Clear project link
                if self.project_link_label:
                    self.project_link_label['text'] = ""
                    self.plugin.current_build_id = None
                
                # Fetch body data in background for future use
                if self.plugin.current_system and not hasattr(self.plugin, '_bodies_fetched'):
                    logger.debug("Pre-fetching body data for Create dialog")
                    # Get system address from journal if needed
                    if not self.plugin.current_system_address:
                        self.plugin.current_system_address = self.plugin.get_system_address_from_journal()
                    self.plugin._bodies_fetched = True
                
                # Enable create button and restore original command
                logger.debug("Enabling Create Project button")
                self.create_button['state'] = tk.NORMAL
                self.create_button['text'] = "🚧 Create Project"
                # Restore original command to open create dialog
                if self.plugin.frame:
                    self.create_button['command'] = lambda: self._open_create_dialog(self.plugin.frame.master)
        else:
            # Not at construction ship - disable button and restore original command
            logger.debug("Disabling Create Project button")
            self.create_button['state'] = tk.DISABLED
            
            # Restore original command to open create dialog
            if self.plugin.frame:
                self.create_button['command'] = lambda: self._open_create_dialog(self.plugin.frame.master)
            
            if self.project_link_label:
                self.project_link_label['text'] = ""
                self.plugin.current_build_id = None
            
            if not self.plugin.is_docked:
                self.create_button['text'] = "Create Project (Dock First)"
            elif not self.plugin.is_construction_ship:
                self.create_button['text'] = "Create Project (Dock at Construction Ship)"
            else:
                self.create_button['text'] = "Create Project"
    
    def _open_project_link(self):
        """Open the existing project in browser"""
        if self.plugin and self.plugin.current_build_id:
            import webbrowser
            url = f"https://ravencolonial.com/#build={self.plugin.current_build_id}"
            logger.info(f"Opening project page: {url}")
            webbrowser.open(url)
    
    def _open_create_dialog(self, parent):
        """Open the Create Project dialog"""
        if self.plugin:
            try:
                import create_project_dialog
                dialog = create_project_dialog.CreateProjectDialog(parent, self.plugin)
            except Exception as e:
                logger.error(f"Failed to open create dialog: {e}", exc_info=True)
                from tkinter import messagebox
                messagebox.showerror("Error", f"Failed to open dialog: {str(e)}")
