"""
Construction Completion Handler for Ravencolonial EDMC Plugin

This module handles the detection and processing of construction completion events
from Elite Dangerous journal entries, following the same logic as SrvSurvey.
"""

import logging
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
        logger.debug("=" * 80)
        logger.debug("CONSTRUCTION COMPLETION HANDLER - START")
        logger.debug(f"Entry keys: {list(entry.keys())}")
        logger.debug(f"ConstructionComplete flag: {entry.get('ConstructionComplete')}")
        
        # Check if construction is complete
        if not entry.get('ConstructionComplete', False):
            logger.debug("Construction not complete - returning False")
            return False
        
        logger.info(f"🎉 Construction complete detected at {self.api_client.current_station}!")
        logger.debug(f"Current state - System: {self.api_client.current_system}, Station: {self.api_client.current_station}")
        logger.debug(f"Current state - SystemAddress: {self.api_client.current_system_address}, MarketID: {self.api_client.current_market_id}")
        
        # Validate we have the required data
        if not self.api_client.current_system_address or not self.api_client.current_market_id:
            logger.warning(f"Construction complete but missing required data - SystemAddress: {self.api_client.current_system_address}, MarketID: {self.api_client.current_market_id}")
            logger.debug("CONSTRUCTION COMPLETION HANDLER - END (missing data)")
            logger.debug("=" * 80)
            return True  # Still return True since we detected completion
        
        # Find the associated project
        logger.debug(f"Fetching project for SystemAddress: {self.api_client.current_system_address}, MarketID: {self.api_client.current_market_id}")
        project = self.api_client.get_project(self.api_client.current_system_address, self.api_client.current_market_id)
        logger.debug(f"Project fetch result: {project}")
        
        if not project or not project.get('buildId'):
            logger.warning(f"Construction complete but no project found - project data: {project}")
            logger.debug("CONSTRUCTION COMPLETION HANDLER - END (no project)")
            logger.debug("=" * 80)
            return True
        
        build_id = project['buildId']
        logger.info(f"Found project to mark complete - BuildID: {build_id}")
        logger.debug(f"Full project data: {project}")
        
        # Mark the project as complete on the server asynchronously
        logger.debug(f"Queueing async API call to mark project {build_id} as complete")
        self.mark_project_complete_async(build_id)
        
        # Update status for user
        logger.debug("Showing completion notification to user")
        self._show_completion_notification(build_id)
        
        logger.debug("CONSTRUCTION COMPLETION HANDLER - END (success)")
        logger.debug("=" * 80)
        return True
    
    def _mark_project_complete(self, build_id: str) -> bool:
        """
        Mark a project as complete in Ravencolonial
        
        :param build_id: The project build ID
        :return: True if successful, False otherwise
        """
        logger.debug(f"_mark_project_complete called for BuildID: {build_id}")
        logger.debug(f"API client type: {type(self.api_client.api_client)}")
        logger.debug(f"API client has method: {hasattr(self.api_client.api_client, 'mark_project_complete')}")
        
        try:
            result = self.api_client.api_client.mark_project_complete(build_id)
            logger.debug(f"mark_project_complete returned: {result}")
            return result
        except Exception as e:
            logger.error(f"Exception in _mark_project_complete: {type(e).__name__}: {e}", exc_info=True)
            raise
    
    def mark_project_complete_async(self, build_id: str):
        """
        Mark a project as complete asynchronously using the API queue
        
        :param build_id: The project build ID
        """
        logger.debug(f"mark_project_complete_async called for BuildID: {build_id}")
        logger.debug(f"Queueing API call with function: {self._mark_project_complete.__name__}")
        self.api_client.queue_api_call(self._mark_project_complete, build_id)
        logger.debug("API call queued successfully")
    
    def _show_completion_notification(self, build_id: str):
        """
        Show completion notification to the user
        
        :param build_id: The completed project ID
        """
        logger.debug(f"_show_completion_notification called for BuildID: {build_id}")
        
        # Update status in main plugin
        completion_message = f"🎉 Construction Complete! Project {build_id} marked as finished."
        logger.debug(f"Updating status with message: {completion_message}")
        self.api_client.update_status(completion_message)
        
        logger.info(f"Construction complete - Project {build_id} at {self.api_client.current_station}")
