"""
Construction Completion Handler for Ravencolonial EDMC Plugin

This module handles the detection and processing of construction completion events
from Elite Dangerous journal entries, following the same logic as SrvSurvey.
"""

import logging
import urllib.parse
import plug
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConstructionCompletionHandler:
    """Handles construction completion events and server notifications"""
    
    def __init__(self, api_client):
        """
        Initialize the completion handler
        
        :param api_client: The main plugin instance with API methods
        """
        self.api_client = api_client
    
    def handle_construction_complete(self, entry: Dict[str, Any]) -> bool:
        """
        Handle a ColonisationConstructionDepot journal event
        
        :param entry: The journal entry data
        :return: True if construction was complete and handled, False otherwise
        """
        # Check if construction is complete
        if not entry.get('ConstructionComplete', False):
            return False
        
        logger.info(f"🎉 Construction complete detected at {self.api_client.current_station}!")
        
        # Validate we have the required data
        if not self.api_client.current_system_address or not self.api_client.current_market_id:
            logger.warning("Construction complete but missing system address or market ID")
            return True  # Still return True since we detected completion
        
        # Find the associated project
        project = self.api_client.get_project(self.api_client.current_system_address, self.api_client.current_market_id)
        if not project or not project.get('buildId'):
            logger.warning("Construction complete but no project found to mark as complete")
            return True
        
        build_id = project['buildId']
        logger.info(f"Marking project {build_id} as complete")
        
        # Mark the project as complete on the server asynchronously
        self.mark_project_complete_async(build_id)
        
        # Show immediate notification to user
        self._show_completion_notification(build_id)
        
        return True
    
    def _mark_project_complete(self, build_id: str) -> bool:
        """
        Mark a project as complete in Ravencolonial
        
        :param build_id: The project build ID
        :return: True if successful, False otherwise
        """
        try:
            url = f"{self.api_client.api_base}/api/project/{urllib.parse.quote(build_id)}/complete"
            logger.debug(f"Mark complete URL: {url}")
            
            response = self.api_client.session.post(url, timeout=10)
            logger.debug(f"Mark complete response status: {response.status_code}")
            logger.debug(f"Mark complete response body: {response.text}")
            response.raise_for_status()
            
            logger.info(f"Successfully marked project {build_id} as complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark project complete: {e}")
            logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            return False
    
    def mark_project_complete_async(self, build_id: str):
        """
        Mark a project as complete asynchronously using the API queue
        
        :param build_id: The project build ID
        """
        self.api_client.queue_api_call(self._mark_project_complete, build_id)
    
    def _show_completion_notification(self, build_id: str):
        """
        Show completion notification to the user
        
        :param build_id: The completed project ID
        """
        # Update status in main plugin
        completion_message = f"🎉 Construction Complete! Project {build_id} marked as finished."
        self.api_client.update_status(completion_message)
        
        # Show popup notification
        popup_message = f"🎉 Construction Complete at {self.api_client.current_station}! Project has been marked as finished."
        plug.show_error(popup_message)
        
        logger.info(completion_message)
