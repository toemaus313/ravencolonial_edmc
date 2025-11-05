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
RELEASES_URL = "https://api.github.com/repos/toemaus313/ravencolonial_edmc/releases"


def safe_remove_backup(backup_dir, logger):
    """Safely remove backup directory, handling symbolic links"""
    if os.path.exists(backup_dir):
        if os.path.islink(backup_dir):
            os.unlink(backup_dir)  # Remove symbolic link
            if logger:
                logger.debug(f"Removed symbolic link backup: {backup_dir}")
        elif os.path.isdir(backup_dir):
            shutil.rmtree(backup_dir)  # Remove directory
            if logger:
                logger.debug(f"Removed directory backup: {backup_dir}")


def compare_versions(current: str, latest: str, logger=None) -> bool:
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
        
        # Extract numeric parts and check for pre-release suffixes
        def parse_version(version: str):
            parts = version.split('.')
            numeric_parts = []
            is_prerelease = False
            
            for part in parts:
                # Extract only the leading digits from each part
                numeric_part = ''
                suffix_part = ''
                digit_collection_complete = False
                
                for char in part:
                    if char.isdigit() and not digit_collection_complete:
                        numeric_part += char
                    else:
                        digit_collection_complete = True
                        suffix_part += char.lower()
                
                if numeric_part:
                    numeric_parts.append(numeric_part)
                    # Check if this part has a pre-release suffix
                    if logger:
                        logger.debug(f"Checking part '{part}' - numeric: '{numeric_part}', suffix: '{suffix_part}'")
                    if any(suffix in suffix_part for suffix in ['alpha', 'beta', 'rc', 'pre']):
                        is_prerelease = True
                        if logger:
                            logger.debug(f"Found prerelease suffix in '{suffix_part}'")
            
            return numeric_parts, is_prerelease
        
        current_numeric, current_is_prerelease = parse_version(current)
        latest_numeric, latest_is_prerelease = parse_version(latest)
        
        if logger:
            logger.debug(f"Parsed versions - Current: {current_numeric} (prerelease: {current_is_prerelease}), Latest: {latest_numeric} (prerelease: {latest_is_prerelease})")
        
        # Parse version strings into tuples of integers
        # e.g., "1.5.2" becomes (1, 5, 2)
        current_parts = tuple(int(x) for x in current_numeric[:3])
        latest_parts = tuple(int(x) for x in latest_numeric[:3])
        
        if logger:
            logger.debug(f"Version tuples - Current: {current_parts}, Latest: {latest_parts}")
        
        # Compare numeric versions
        if latest_parts > current_parts:
            if logger:
                logger.debug(f"Latest is newer numerically: {latest_parts} > {current_parts}")
            return True
        elif latest_parts < current_parts:
            if logger:
                logger.debug(f"Latest is older numerically: {latest_parts} < {current_parts}")
            return False
        else:
            # Same numeric version - stable release is newer than prerelease
            if logger:
                logger.debug(f"Same numeric version, checking prerelease status - Latest prerelease: {latest_is_prerelease}, Current prerelease: {current_is_prerelease}")
            if not latest_is_prerelease and current_is_prerelease:
                if logger:
                    logger.debug(f"Stable release is newer than prerelease")
                return True
            if logger:
                logger.debug(f"No update needed")
            return False
            
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
            
            releases = response.json()
            
            # Find the latest suitable release
            suitable_release = None
            for release in releases:
                tag = release.get('tag_name', '')
                
                if not tag:
                    continue
                
                # Check if it's a pre-release
                if release.get('prerelease', False):
                    if not self._beta:
                        self._logger.debug(f"Skipping pre-release {tag} (pre-releases disabled)")
                        continue
                    else:
                        self._logger.debug(f"Considering pre-release {tag} (pre-releases enabled)")
                
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
                    continue
                
                # This is a suitable release
                suitable_release = release
                break
            
            if not suitable_release:
                self._logger.info("No suitable release found")
                return None
            
            # Get the HTML URL for the release page
            tag = suitable_release.get('tag_name', '')
            html_url = suitable_release.get('html_url', f"https://github.com/toemaus313/ravencolonial_edmc/releases/tag/{tag}")
            
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
            
            is_outdated = compare_versions(current_ver, remote_ver, self._logger)
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
                # The ZIP should extract to: Ravencolonial-EDMC-vX.Y.Z/
                # containing the plugin files directly
                zip_dirs = [
                    f for f in os.listdir(tmp_dir)
                    if os.path.isdir(os.path.join(tmp_dir, f))
                ]
                
                if len(zip_dirs) != 1:
                    raise ValueError(
                        f"Expected 1 folder in ZIP, found {len(zip_dirs)}: {zip_dirs}"
                    )
                
                extracted_plugin_dir = os.path.join(tmp_dir, zip_dirs[0])
                self._logger.debug(f"Extracted folder: {extracted_plugin_dir}")
                
                # Check if this folder contains load.py (indicating it's the plugin folder)
                # or if it contains a subdirectory with the plugin files
                load_py_path = os.path.join(extracted_plugin_dir, "load.py")
                if os.path.exists(load_py_path):
                    # Plugin files are directly in this folder
                    plugin_source_dir = extracted_plugin_dir
                    self._logger.debug(f"Plugin files found directly in: {plugin_source_dir}")
                else:
                    # Look for a subdirectory that contains load.py
                    subdirs = [
                        f for f in os.listdir(extracted_plugin_dir)
                        if os.path.isdir(os.path.join(extracted_plugin_dir, f))
                    ]
                    plugin_source_dir = None
                    for subdir in subdirs:
                        if os.path.exists(os.path.join(extracted_plugin_dir, subdir, "load.py")):
                            plugin_source_dir = os.path.join(extracted_plugin_dir, subdir)
                            break
                    
                    if not plugin_source_dir:
                        raise ValueError("Could not find plugin files (load.py) in extracted ZIP")
                    
                    self._logger.debug(f"Plugin files found in subdirectory: {plugin_source_dir}")
                
                self._logger.debug(f"Plugin source directory: {plugin_source_dir}")
                
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
                safe_remove_backup(backup_dir, self._logger)
                
                try:
                    # Move current version to backup
                    self._logger.info(f"Backing up current version: {live_file_dir} -> {backup_dir}")
                    shutil.move(live_file_dir, backup_dir)
                    
                    # Move new version to live location
                    self._logger.info(f"Installing new version: {plugin_source_dir} -> {live_file_dir}")
                    shutil.move(plugin_source_dir, live_file_dir)
                    
                    # Success! Clean up backup
                    self._logger.info("Update successful, removing backup")
                    safe_remove_backup(backup_dir, self._logger)
                    
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
