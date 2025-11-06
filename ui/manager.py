"""
UI Manager for Ravencolonial EDMC Plugin

Handles UI state management and updates.
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Optional
from threading import Thread

logger = logging.getLogger(__name__)

# ========== TEMPORARY TESTING BYPASS ==========
# Set to True to always enable Create Project button for testing
# TODO: Remove this bypass after testing is complete
TESTING_BYPASS_CREATE_BUTTON = False
# ==============================================


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
        self.update_frame: Optional[tk.Frame] = None
        self.main_controls_frame: Optional[tk.Frame] = None
    
    def create_plugin_frame(self, parent: tk.Frame) -> tk.Frame:
        """
        Create the main plugin frame for EDMC
        
        :param parent: The parent frame
        :return: The created frame
        """
        frame = tk.Frame(parent)
        self.plugin.frame = frame
        
        # Main controls frame (contains status and buttons)
        self.main_controls_frame = tk.Frame(frame)
        self.main_controls_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Button row frame (contains button and project link)
        button_row = tk.Frame(self.main_controls_frame)
        button_row.pack(side=tk.TOP, fill=tk.X)
        
        # Project link label (shows when project exists)
        self.project_link_label = tk.Label(button_row, text="", cursor="hand2", fg='blue')
        self.project_link_label.pack(side=tk.LEFT, padx=5)
        self.project_link_label.bind("<Button-1>", lambda e: self._open_project_link())
        self.plugin.project_link_label = self.project_link_label
        self.plugin.current_build_id = None
        
        # Create project button
        self.create_button = tk.Button(
            button_row, 
            text="Create Project (Dock First)",
            command=lambda: self._open_create_dialog(parent),
            state=tk.DISABLED
        )
        self.create_button.pack(side=tk.LEFT, padx=5)
        self.plugin.create_button = self.create_button
        
        # Status row frame (contains status label)
        status_row = tk.Frame(self.main_controls_frame)
        status_row.pack(side=tk.TOP, fill=tk.X)
        
        # Status label
        self.status_label = tk.Label(status_row, text="Ravencolonial: Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)
        self.plugin.status_label = self.status_label
        
        # Check for updates after a short delay to allow UI to settle
        frame.after(3000, self._check_and_show_update_notification)
        
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
        
        # ========== TEMPORARY TESTING BYPASS ==========
        if TESTING_BYPASS_CREATE_BUTTON:
            logger.warning("TESTING BYPASS ACTIVE - Create Project button always enabled")
            self.create_button['state'] = tk.NORMAL
            self.create_button['text'] = "🚧 Create Project [TEST MODE]"
            if self.plugin.frame:
                self.create_button['command'] = lambda: self._open_create_dialog(self.plugin.frame.master)
            return
        # ==============================================
        
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
    
    def _check_and_show_update_notification(self):
        """Check if update is available and show notification if needed"""
        if self.plugin.update_available and not self.plugin.update_dismissed:
            self._show_update_notification()
    
    def _show_update_notification(self):
        """Display update notification banner with action buttons"""
        if self.update_frame:
            return  # Already showing
        
        if not self.plugin.frame:
            return
        
        # Create update notification frame
        self.update_frame = tk.Frame(self.plugin.frame, relief=tk.RIDGE, borderwidth=2)
        self.update_frame.pack(side=tk.TOP, fill=tk.X, padx=2, pady=2, before=self.main_controls_frame)
        
        # Get version info
        try:
            from version_check import CURRENT_VERSION
            current = CURRENT_VERSION()
        except:
            current = "unknown"
        
        remote = self.plugin.update_info.remote_version or "unknown"
        
        # Info label
        info_text = f"Update Available: v{current} → v{remote}"
        info_label = tk.Label(self.update_frame, text=info_text, fg='orange')
        info_label.grid(row=0, column=0, columnspan=3, padx=5, pady=2)
        
        # Buttons
        btn_download = tk.Button(
            self.update_frame,
            text="📥 Go to Download",
            command=self._open_download_page
        )
        btn_download.grid(row=1, column=0, padx=2, pady=2)
        
        btn_autoupdate = tk.Button(
            self.update_frame,
            text="⚡ Auto-Update",
            command=self._trigger_autoupdate
        )
        btn_autoupdate.grid(row=1, column=1, padx=2, pady=2)
        
        btn_dismiss = tk.Button(
            self.update_frame,
            text="✖ Dismiss",
            command=self._dismiss_update_notification
        )
        btn_dismiss.grid(row=1, column=2, padx=2, pady=2)
    
    def _dismiss_update_notification(self):
        """Hide the update notification banner"""
        if self.update_frame:
            self.update_frame.destroy()
            self.update_frame = None
        self.plugin.update_dismissed = True
    
    def _open_download_page(self):
        """Open the GitHub release page in browser"""
        if self.plugin.update_info:
            self.plugin.update_info.open_download_page()
    
    def _trigger_autoupdate(self):
        """Manually trigger auto-update in background thread"""
        if not self.plugin.update_info:
            return
        
        # Disable buttons during update
        if self.update_frame:
            for widget in self.update_frame.winfo_children():
                if isinstance(widget, tk.Button):
                    widget.config(state=tk.DISABLED)
        
        # Show updating message
        self.update_status("Ravencolonial: Updating...")
        
        def update_thread():
            """Background thread for update installation"""
            try:
                logger.info("Manual auto-update triggered")
                self.plugin.update_info.run_autoupdate()
                
                # Success message
                import plug
                plug.show_error(
                    f"Ravencolonial: Update complete! "
                    f"Restart EDMC to use v{self.plugin.update_info.remote_version}"
                )
                
                # Update UI
                if self.update_frame:
                    self.plugin.frame.after(0, self._dismiss_update_notification)
                if self.status_label:
                    self.plugin.frame.after(0, lambda: self.update_status("Ravencolonial: Update installed - Restart EDMC"))
                
            except Exception as e:
                logger.error(f"Manual auto-update failed: {e}", exc_info=True)
                
                # Error message
                import plug
                plug.show_error(f"Ravencolonial: Update failed - {str(e)}")
                
                # Re-enable buttons
                if self.update_frame:
                    def re_enable():
                        for widget in self.update_frame.winfo_children():
                            if isinstance(widget, tk.Button):
                                widget.config(state=tk.NORMAL)
                    self.plugin.frame.after(0, re_enable)
                
                if self.status_label:
                    self.plugin.frame.after(0, lambda: self.update_status("Ravencolonial: Update failed"))
        
        # Start update in background
        Thread(target=update_thread, daemon=True, name="manual-autoupdate").start()
