"""
Ravencolonial API Client

Handles all communication with the Ravencolonial API endpoints.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import logging
import urllib.parse
from typing import Optional, Dict, Any, List
from config import appname
import os

# Use EDMC-compliant logger namespace
plugin_name = os.path.basename(os.path.dirname(os.path.dirname(__file__)))
logger = logging.getLogger(f'{appname}.{plugin_name}.api')
# Disable propagation to avoid inheriting EDMC's osthreadid formatter
logger.propagate = False
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(name)s: %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class RavencolonialAPIClient:
    """Client for interacting with Ravencolonial API"""
    
    def __init__(self, api_base: str, user_agent: str):
        """
        Initialize the API client
        
        :param api_base: Base URL for the API
        :param user_agent: User agent string for requests
        """
        self.api_base = api_base
        self.cmdr_name = None
        self.api_key = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent,
            'Content-Type': 'application/json'
        })
        
        # Configure retry logic: 2 retries with exponential backoff for timeouts and connection errors
        retry_strategy = Retry(
            total=2,  # Retry up to 2 times (3 attempts total)
            backoff_factor=1,  # Wait 1s, then 2s between retries
            status_forcelist=[500, 502, 503, 504],  # Retry on server errors
            allowed_methods=["GET", "POST", "PATCH", "PUT"],  # Retry safe methods
            raise_on_status=False  # Don't raise exception, let response.raise_for_status() handle it
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        logger.info("API client initialized with retry logic (2 retries, exponential backoff)")
    
    def set_credentials(self, cmdr_name: str, api_key: str):
        """
        Set commander credentials for Fleet Carrier API calls
        
        :param cmdr_name: Commander name
        :param api_key: Ravencolonial API key
        """
        self.cmdr_name = cmdr_name
        self.api_key = api_key
        logger.debug(f"Set credentials for commander: {cmdr_name}")
    
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
    
    def contribute_cargo(self, build_id: str, cmdr: str, cargo_diff: Dict[str, int]) -> bool:
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
    
    def update_project_supply(self, build_id: str, payload: Dict) -> bool:
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
    
    def get_system_sites(self, system_address: int) -> List[Dict]:
        """Get available construction sites in a system"""
        logger.debug(f"get_system_sites called for system address: {system_address}")
        
        try:
            url = f"{self.api_base}/api/v2/system/{system_address}/sites"
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
    
    def get_system_architect(self, system_address: int) -> Optional[str]:
        """Get the architect name for a system using the v2 system API"""
        try:
            url = f"{self.api_base}/api/v2/system/{system_address}"
            logger.debug(f"Getting system architect from URL: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            system_data = response.json()
            
            # Extract architect from system data
            architect = system_data.get('architect')
            logger.debug(f"System architect response: {architect}")
            return architect
        except Exception as e:
            logger.error(f"Failed to get system architect: {e}")
            return None
    
    def mark_project_complete(self, build_id: str) -> bool:
        """Mark a project as complete in Ravencolonial"""
        try:
            url = f"{self.api_base}/api/project/{urllib.parse.quote(build_id)}/complete"
            logger.debug(f"Mark complete URL: {url}")
            response = self.session.post(url, timeout=10)
            logger.debug(f"Mark complete response status: {response.status_code}")
            logger.debug(f"Mark complete response body: {response.text}")
            response.raise_for_status()
            logger.info(f"Successfully marked project {build_id} as complete")
            return True
        except Exception as e:
            logger.error(f"Failed to mark project complete: {e}")
            logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            return False
    
    # Fleet Carrier methods
    def get_fc(self, market_id: int) -> Optional[Dict[str, Any]]:
        """Get Fleet Carrier data from Ravencolonial"""
        try:
            url = f"{self.api_base}/api/fc/{market_id}"
            logger.debug(f"Getting FC data from URL: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            fc_data = response.json()
            logger.debug(f"FC data response: {fc_data}")
            return fc_data
        except Exception as e:
            logger.error(f"Failed to get FC data: {e}")
            return None
    
    def update_fc_cargo(self, market_id: int, cargo: Dict[str, int]) -> Optional[Dict[str, int]]:
        """Fully replace Fleet Carrier cargo with new totals"""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                url = f"{self.api_base}/api/fc/{market_id}/cargo"
                if attempt > 0:
                    logger.warning(f"Retry attempt {attempt}/{max_attempts - 1} for FC cargo update")
                logger.debug(f"Updating FC cargo at URL: {url}")
                logger.debug(f"New cargo: {cargo}")
                
                # Add required headers
                headers = {
                    'rcc-cmdr': self.cmdr_name if hasattr(self, 'cmdr_name') else None,
                    'rcc-key': self.api_key if hasattr(self, 'api_key') else None
                }
                headers = {k: v for k, v in headers.items() if v is not None}
                
                response = self.session.post(url, json=cargo, headers=headers, timeout=15)
                logger.debug(f"Update FC cargo response status: {response.status_code}")
                logger.debug(f"Update FC cargo response body: {response.text}")
                response.raise_for_status()
                
                updated_cargo = response.json()
                logger.info(f"Successfully updated FC {market_id} cargo")
                return updated_cargo
            except requests.exceptions.Timeout as e:
                if attempt < max_attempts - 1:
                    logger.warning(f"Timeout on attempt {attempt + 1}/{max_attempts}: {e}")
                    continue  # Retry
                else:
                    logger.error(f"Failed to update FC cargo after {max_attempts} attempts (timeout): {e}")
                    return None
            except Exception as e:
                logger.error(f"Failed to update FC cargo: {e}")
                logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
                return None
    
    def supply_fc(self, market_id: int, cargo_diff: Dict[str, int]) -> Optional[Dict[str, int]]:
        """Incrementally update Fleet Carrier cargo (add/remove specific quantities)"""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                url = f"{self.api_base}/api/fc/{market_id}/cargo"
                if attempt > 0:
                    logger.warning(f"Retry attempt {attempt}/{max_attempts - 1} for FC cargo supply")
                logger.debug(f"Supplying FC cargo at URL: {url}")
                logger.debug(f"Cargo diff: {cargo_diff}")
                
                # Add required headers
                headers = {
                    'rcc-cmdr': self.cmdr_name if hasattr(self, 'cmdr_name') else None,
                    'rcc-key': self.api_key if hasattr(self, 'api_key') else None
                }
                headers = {k: v for k, v in headers.items() if v is not None}
                
                response = self.session.patch(url, json=cargo_diff, headers=headers, timeout=15)
                logger.debug(f"Supply FC response status: {response.status_code}")
                logger.debug(f"Supply FC response body: {response.text}")
                response.raise_for_status()
                
                updated_cargo = response.json()
                logger.info(f"Successfully supplied FC {market_id} with cargo diff")
                return updated_cargo
            except requests.exceptions.Timeout as e:
                if attempt < max_attempts - 1:
                    logger.warning(f"Timeout on attempt {attempt + 1}/{max_attempts}: {e}")
                    continue  # Retry
                else:
                    logger.error(f"Failed to supply FC cargo after {max_attempts} attempts (timeout): {e}")
                    return None
            except Exception as e:
                logger.error(f"Failed to supply FC cargo: {e}")
                logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
                return None
    
    def get_all_cmdr_fcs(self, cmdr_name: str) -> List[Dict[str, Any]]:
        """Get all Fleet Carriers linked to a commander
        
        Returns a list of FC objects with marketId, name, displayName, and cargo dict
        """
        try:
            url = f"{self.api_base}/api/cmdr/{urllib.parse.quote(cmdr_name)}/fc/all"
            logger.debug(f"Getting all CMDR FCs from URL: {url}")
            response = self.session.get(url, timeout=10)
            
            # 404 means no FCs linked yet - this is normal, not an error
            if response.status_code == 404:
                logger.info(f"No Fleet Carriers linked for commander {cmdr_name}")
                return []
            
            response.raise_for_status()
            fcs = response.json()
            logger.debug(f"CMDR FCs response: {fcs}")
            return fcs if isinstance(fcs, list) else []
        except Exception as e:
            logger.error(f"Failed to get CMDR FCs: {e}")
            return []
