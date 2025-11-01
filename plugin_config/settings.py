"""
Configuration settings for Ravencolonial EDMC Plugin
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PluginConfig:
    """Configuration management for the Ravencolonial plugin"""
    
    # Plugin metadata
    NAME = os.path.basename(os.path.dirname(os.path.dirname(__file__)))
    VERSION = "1.5.0"
    
    # API configuration
    DEFAULT_API_BASE = "https://ravencolonial100-awcbdvabgze4c5cq.canadacentral-01.azurewebsites.net"
    
    # Logging configuration
    LOG_LEVEL = logging.INFO
    # Use simple format - EDMC will handle the full formatting
    LOG_FORMAT = '%(name)s: %(levelname)s - %(message)s'
    LOG_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
    LOG_TIME_MSEC_FORMAT = '%s.%03d'
    
    @staticmethod
    def get_api_base() -> str:
        """Get the API base URL from config or use default"""
        try:
            from config import appname_config
            return appname_config.get_str("ravencolonial_api_url") or PluginConfig.DEFAULT_API_BASE
        except (ImportError, AttributeError):
            # Fallback if EDMC config is not available
            return PluginConfig.DEFAULT_API_BASE
    
    @staticmethod
    def get_user_agent() -> str:
        """Get the user agent string for API requests"""
        return f'EDMC-Ravencolonial/{PluginConfig.VERSION}'
    
    @staticmethod
    def setup_logging():
        """Setup logging configuration"""
        # If the Logger has handlers then it was already set up by the core code, else
        # it needs setting up here.
        try:
            from config import appname
            logger_name = f'{appname}.{PluginConfig.NAME}'
        except ImportError:
            # Fallback if EDMC config is not available
            logger_name = f'EDMC.{PluginConfig.NAME}'
        
        logger = logging.getLogger(logger_name)
        
        if not logger.hasHandlers():
            level = PluginConfig.LOG_LEVEL
            logger.setLevel(level)
            logger_channel = logging.StreamHandler()
            logger_formatter = logging.Formatter(PluginConfig.LOG_FORMAT)
            logger_formatter.default_time_format = PluginConfig.LOG_TIME_FORMAT
            logger_formatter.default_msec_format = PluginConfig.LOG_TIME_MSEC_FORMAT
            logger_channel.setFormatter(logger_formatter)
            logger.addHandler(logger_channel)
        
        return logger
