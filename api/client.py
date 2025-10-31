"""
Ravencolonial API Client

Handles all communication with the Ravencolonial API endpoints.
"""

import requests
import json
import logging
import urllib.parse
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class RavencolonialAPIClient:
    """Client for interacting with Ravencolonial API"""
    
    def __init__(self, api_base: str, user_agent: str):
        """
        Initialize the API client
        
        :param api_base: Base URL for the API
        :param user_agent: User agent string for requests
        """
        self.api_base = api_base
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent,
            'Content-Type': 'application/json'
        })
    
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
