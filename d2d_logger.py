"""
Dock-to-Dock Time Logger

Monitors Elite Dangerous journal for "Docked" events and logs timestamps
with time between dockings to a CSV file.
"""

import csv
import os
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class D2DLogger:
    """Handles logging of docked events and time between dockings"""
    
    def __init__(self):
        self.csv_file_path = self._get_csv_path()
        self.last_docked_time: Optional[datetime] = None
        
    def _get_csv_path(self) -> str:
        """Get cross-platform path for ~/Documents/d2dTimes.csv"""
        # Get the Documents directory in a cross-platform way
        documents_dir = os.path.join(os.path.expanduser('~'), 'Documents')
        csv_path = os.path.join(documents_dir, 'd2dTimes.csv')
        
        # Ensure Documents directory exists
        os.makedirs(documents_dir, exist_ok=True)
        
        logger.debug(f"D2D CSV path: {csv_path}")
        return csv_path
    
    def _ensure_csv_exists(self):
        """Create CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.csv_file_path):
            logger.info(f"Creating new D2D CSV file: {self.csv_file_path}")
            with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['LandingTime', 'd2dTime'])
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse Elite Dangerous timestamp to datetime object"""
        # Elite Dangerous timestamps are in ISO format: "2023-12-07T15:30:45Z"
        try:
            # Remove the 'Z' suffix and parse
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1]
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse timestamp '{timestamp_str}': {e}")
            # Fallback to current time if parsing fails
            return datetime.now()
    
    def _format_timedelta(self, delta) -> str:
        """Format timedelta as a human-readable string"""
        if delta is None:
            return ""
        
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours}h {minutes}m {seconds}s"
    
    def log_docked_event(self, timestamp: str, station_name: str = "", system_name: str = ""):
        """
        Log a docked event to the CSV file
        
        :param timestamp: Elite Dangerous timestamp string
        :param station_name: Name of the station (for logging purposes)
        :param system_name: Name of the system (for logging purposes)
        """
        try:
            # Ensure CSV file exists
            self._ensure_csv_exists()
            
            # Parse the timestamp
            current_time = self._parse_timestamp(timestamp)
            
            # Calculate time since last docked
            d2d_time_str = ""
            if self.last_docked_time:
                time_delta = current_time - self.last_docked_time
                d2d_time_str = self._format_timedelta(time_delta)
                logger.debug(f"Time since last dock: {d2d_time_str}")
            
            # Write to CSV
            with open(self.csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([timestamp, d2d_time_str])
            
            logger.info(f"Logged docked event at {station_name} ({system_name}) - d2d time: {d2d_time_str}")
            
            # Update last docked time
            self.last_docked_time = current_time
            
        except Exception as e:
            logger.error(f"Failed to log docked event: {e}", exc_info=True)
    
    def load_last_docked_time(self):
        """Load the most recent docked time from existing CSV file"""
        try:
            if not os.path.exists(self.csv_file_path):
                logger.debug("No existing D2D CSV file found")
                return
            
            logger.debug("Loading last docked time from existing CSV")
            with open(self.csv_file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
                
                if rows:
                    # Get the most recent row
                    last_row = rows[-1]
                    last_timestamp = last_row.get('LandingTime')
                    
                    if last_timestamp:
                        self.last_docked_time = self._parse_timestamp(last_timestamp)
                        logger.debug(f"Loaded last docked time: {self.last_docked_time}")
                    else:
                        logger.debug("Last row had no timestamp")
                else:
                    logger.debug("CSV file exists but has no data rows")
                    
        except Exception as e:
            logger.error(f"Failed to load last docked time: {e}", exc_info=True)
