"""
Version checking and auto-update module for Ravencolonial-EDMC
Adapted from EDMC-RavenColonial plugin by CMDR-WDX
"""

import dataclasses
import random
import shutil
import string
import zipfile
from logging import Logger
import os
import tempfile
from typing import Optional

import requests

# GitHub API endpoint for releases
RELEASES_URL = "https://api.github.com/repos/toemaus313/ravencolonial_edmc/releases/latest"


def compare_versions(current: str, latest: str) -> bool:
    """
    Compare version strings to see if latest is newer than current.
    Uses simple semantic versioning comparison (major.minor.patch).
    
    :param current: Current version string (e.g., "1.5.2")
    :param latest: Latest version string (e.g., "1.5.3")
    :return: True if latest is newer than current
    """
    try:
        # Remove 'v' prefix if present
        current = current.lstrip('v')
        latest = latest.lstrip('v')
        
        # Parse version strings into tuples of integers
        # e.g., "1.5.2" becomes (1, 5, 2)
        current_parts = tuple(int(x) for x in current.split('.'))
        latest_parts = tuple(int(x) for x in latest.split('.'))
        
        # Python compares tuples element by element
        return latest_parts > current_parts
    except (ValueError, AttributeError) as e:
        # If parsing fails, assume no update
        return False


def CURRENT_VERSION():
    """
    Get current plugin version
    This should match the plugin_version in load.py
    """
    from plugin_config import PluginConfig
    return PluginConfig.VERSION


class UpdateInfo:
    """Handles version checking and auto-update functionality"""
    
    @dataclasses.dataclass
    class Data:
        """Release data from GitHub"""
        tag_name: str
        browser_link: str
        zip_link: str
    
    def __init__(self, logger: Logger, plugin_name: str, allow_prerelease=False):
        self._logger = logger
        self.plugin_name = plugin_name
        self._beta = allow_prerelease
        self._data: Optional[UpdateInfo.Data] = None
    
    @property
    def remote_version(self):
        """Get the remote version tag"""
        if self._data is None:
            return None
        return self._data.tag_name
    
    def check(self) -> Optional[Data]:
        """
        Check GitHub for latest release
        Thread-safe - should be called from background thread
        
        :return: UpdateInfo.Data if release found, None otherwise
        """
        try:
            self._logger.info(f"Checking for updates at {RELEASES_URL}")
            response = requests.get(RELEASES_URL, timeout=10)
            
            if response.status_code != 200:
                self._logger.warning(f"GitHub API returned status {response.status_code}")
                return None
            
            release = response.json()
            tag = release.get('tag_name', '')
            
            if not tag:
                self._logger.warning("No tag_name in release response")
                return None
            
            # Check if it's a pre-release
            if release.get('prerelease', False):
                if not self._beta:
                    self._logger.debug(f"Skipping pre-release {tag} (pre-releases disabled)")
                    return None
            
            # Find the plugin ZIP in assets
            assets = release.get('assets', [])
            asset_url: Optional[str] = None
            
            for asset in assets:
                asset_name = asset.get('name', '')
                # Look for ZIP file matching pattern: Ravencolonial-EDMC-vX.Y.Z.zip
                if asset_name.endswith('.zip') and tag.lstrip('v') in asset_name:
                    asset_url = asset.get('browser_download_url')
                    self._logger.debug(f"Found asset: {asset_name} -> {asset_url}")
                    break
            
            if not asset_url:
                self._logger.warning(f"No ZIP asset found for release {tag}")
                return None
            
            # Get the HTML URL for the release page
            html_url = release.get('html_url', f"https://github.com/toemaus313/ravencolonial_edmc/releases/tag/{tag}")
            
            self._data = UpdateInfo.Data(tag, html_url, asset_url)
            self._logger.info(f"Found release: {tag}")
            return self._data
            
        except Exception as e:
            self._logger.error(f"Error checking for updates: {e}", exc_info=True)
            return None
    
    def is_current_version_outdated(self) -> bool:
        """
        Compare current version with remote version
        
        :return: True if remote version is newer
        """
        if self._data is None:
            return False
        
        try:
            current_ver = CURRENT_VERSION()
            remote_ver = self._data.tag_name
            
            is_outdated = compare_versions(current_ver, remote_ver)
            self._logger.debug(f"Version comparison: {current_ver} vs {remote_ver} = outdated: {is_outdated}")
            return is_outdated
            
        except Exception as e:
            self._logger.error(f"Error comparing versions: {e}", exc_info=True)
            return False
    
    def run_autoupdate(self):
        """
        Download and install update
        Thread-safe - should be called from background thread
        
        :raises ValueError: If update data is missing or version is dev build
        :raises Exception: If update process fails
        """
        data = self._data
        if data is None:
            raise ValueError("Missing release info - call check() first")
        
        current_ver = CURRENT_VERSION()
        
        # Safety check: Don't update dev builds
        if current_ver in ["dev", "0.0.0", "0.0.0-DEV"]:
            raise ValueError(
                "Cannot auto-update dev build. "
                "Please update manually or use a release version."
            )
        
        self._logger.info(f"Starting auto-update from {current_ver} to {data.tag_name}")
        self._logger.info(f"Downloading update from {data.zip_link}")
        
        try:
            # Download the ZIP file
            response = requests.get(data.zip_link, timeout=30)
            
            if response.status_code != 200:
                raise ValueError(
                    f"Failed to download update: HTTP {response.status_code}"
                )
            
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as tmp_dir:
                self._logger.debug(f"Using temp directory: {tmp_dir}")
                
                # Save ZIP file
                zip_path = os.path.join(tmp_dir, "update.zip")
                with open(zip_path, "wb") as zip_file:
                    zip_file.write(response.content)
                
                self._logger.debug(f"Downloaded {len(response.content)} bytes")
                
                # Extract ZIP
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(tmp_dir)
                
                self._logger.info(f"Extracted to {tmp_dir}")
                os.remove(zip_path)
                
                # Find the plugin folder inside the extracted content
                # Should be: Ravencolonial-EDMC/
                zip_dirs = [
                    f for f in os.listdir(tmp_dir)
                    if os.path.isdir(os.path.join(tmp_dir, f))
                ]
                
                if len(zip_dirs) != 1:
                    raise ValueError(
                        f"Expected 1 folder in ZIP, found {len(zip_dirs)}: {zip_dirs}"
                    )
                
                extracted_plugin_dir = os.path.join(tmp_dir, zip_dirs[0])
                self._logger.debug(f"Plugin folder: {extracted_plugin_dir}")
                
                # Get current plugin directory (parent of this file)
                live_file_dir = os.path.dirname(os.path.abspath(__file__))
                self._logger.debug(f"Current plugin dir: {live_file_dir}")
                
                # Create backup directory name (random + .disabled to prevent loading)
                backup_dir = os.path.normpath(
                    os.path.join(
                        live_file_dir,
                        "..",
                        "".join(random.choices(string.ascii_lowercase, k=12))
                        + ".backup.disabled"
                    )
                )
                
                # Clean up any existing backup with same name
                if os.path.exists(backup_dir):
                    self._logger.warning(f"Removing existing backup: {backup_dir}")
                    shutil.rmtree(backup_dir)
                
                try:
                    # Move current version to backup
                    self._logger.info(f"Backing up current version: {live_file_dir} -> {backup_dir}")
                    shutil.move(live_file_dir, backup_dir)
                    
                    # Move new version to live location
                    self._logger.info(f"Installing new version: {extracted_plugin_dir} -> {live_file_dir}")
                    shutil.move(extracted_plugin_dir, live_file_dir)
                    
                    # Success! Clean up backup
                    self._logger.info("Update successful, removing backup")
                    shutil.rmtree(backup_dir)
                    
                except Exception as ex:
                    # Rollback on failure
                    self._logger.error("Update failed, attempting rollback")
                    self._logger.exception(ex)
                    
                    # Remove partially installed new version if it exists
                    if os.path.exists(live_file_dir):
                        self._logger.info("Removing failed installation")
                        shutil.rmtree(live_file_dir)
                    
                    # Restore backup
                    if os.path.exists(backup_dir):
                        self._logger.info(f"Restoring backup: {backup_dir} -> {live_file_dir}")
                        shutil.move(backup_dir, live_file_dir)
                        self._logger.info("Rollback successful")
                    
                    raise ex
            
            self._logger.info(f"Auto-update complete! Updated to {data.tag_name}")
            self._logger.info("Please restart EDMC to use the new version")
            
        except Exception as e:
            self._logger.error(f"Auto-update failed: {e}", exc_info=True)
            raise
    
    def open_download_page(self):
        """
        Open the release page in the user's browser
        """
        if self._data is None:
            return
        
        import webbrowser
        webbrowser.open(self._data.browser_link)
