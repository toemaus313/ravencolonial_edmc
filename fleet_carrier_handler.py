"""
Fleet Carrier Handler for Ravencolonial EDMC Plugin

This module handles Fleet Carrier commodity tracking and updates to Ravencolonial,
following the same logic as SrvSurvey.
"""

import logging
from typing import Dict, Any, Optional, List
from config import appname
import os

# Use EDMC-compliant logger namespace
plugin_name = os.path.basename(os.path.dirname(__file__))
logger = logging.getLogger(f'{appname}.{plugin_name}.fc')
# Disable propagation to avoid inheriting EDMC's osthreadid formatter
logger.propagate = False
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(name)s: %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class FleetCarrierHandler:
    """Handles Fleet Carrier commodity tracking and server updates"""
    
    def __init__(self, api_client):
        """
        Initialize the Fleet Carrier handler
        
        :param api_client: The main plugin instance with API methods
        """
        self.api_client = api_client
        self.linked_fcs: Dict[int, Dict[str, Any]] = {}  # marketId -> FC data
        self.current_station_type = None
        self.current_market_id = None
        self.stealth_mode = False
        self.capi_received_fcs = set()  # Track FCs that have received CAPI data this session
    
    def set_stealth_mode(self, enabled: bool):
        """Enable or disable stealth mode"""
        self.stealth_mode = enabled
        if enabled:
            logger.info("Fleet Carrier stealth mode enabled - commodity data will not be sent to Ravencolonial")
        else:
            logger.info("Fleet Carrier stealth mode disabled - commodity data will be sent to Ravencolonial")
    
    def initialize_fcs(self, cmdr_name: str):
        """Initialize Fleet Carrier data for the commander"""
        try:
            logger.info(f"Initializing Fleet Carriers for commander: {cmdr_name}")
            
            # Check stealth mode setting
            from config import config
            try:
                self.stealth_mode = config.get_bool('ravencolonial_stealth_mode')
            except:
                self.stealth_mode = False
                
            if self.stealth_mode:
                logger.info("Fleet Carrier stealth mode is enabled")
            
            # Get all FCs linked to this commander from Ravencolonial API
            # This gives us the current server-side cargo state as initial baseline
            all_fcs = self.api_client.api_client.get_all_cmdr_fcs(cmdr_name)
            
            # Store as dictionary by marketId for easy lookup
            self.linked_fcs = {fc['marketId']: fc for fc in all_fcs}
            
            if len(self.linked_fcs) == 0:
                logger.info(f"No Fleet Carriers linked for commander {cmdr_name}. To link a Fleet Carrier, visit Ravencolonial.com")
            else:
                logger.info(f"Loaded {len(self.linked_fcs)} linked Fleet Carriers with server-side cargo state")
                for market_id, fc in self.linked_fcs.items():
                    fc_name = fc.get('displayName', fc.get('name', 'Unknown'))
                    cargo = fc.get('cargo', {})
                    total_cargo = sum(cargo.values()) if cargo else 0
                    logger.info(f"FC {market_id} ({fc_name}): {len(cargo)} commodity types, {total_cargo} total units (server baseline)")
                
                # Mark all FCs as having initial state from server
                # CAPI can still provide a fresher snapshot if it arrives
                logger.info(f"Initial cargo state loaded from Ravencolonial API for {len(self.linked_fcs)} FCs")
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Fleet Carriers: {e}", exc_info=True)
            return False
    
    def handle_docked_event(self, entry: Dict[str, Any]) -> bool:
        """
        Handle a Docked journal event
        
        :param entry: The journal entry data
        :return: True if this is a Fleet Carrier, False otherwise
        """
        station_type = entry.get('StationType', '')
        market_id = entry.get('MarketID')
        station_name = entry.get('StationName', '')
        
        logger.debug(f"handle_docked_event: station={station_name}, type={station_type}, marketID={market_id}")
        
        # Update current station info
        self.current_station_type = station_type
        self.current_market_id = market_id
        
        logger.debug(f"Updated current_station_type={self.current_station_type}, current_market_id={self.current_market_id}")
        
        if station_type == 'FleetCarrier':
            logger.info(f"Docked at Fleet Carrier: {station_name} (MarketID: {market_id})")
            logger.debug(f"Linked FCs: {list(self.linked_fcs.keys())}")
            
            # Check if this is a linked FC
            if market_id in self.linked_fcs:
                logger.info(f"This is a linked Fleet Carrier - will track commodity changes")
                # Trigger cargo update check after market data is available
                return True
            else:
                logger.info(f"Fleet Carrier {station_name} (MarketID: {market_id}) is not linked to commander in Ravencolonial")
                return True
        else:
            logger.debug(f"Docked at regular station: {station_name} (Type: {station_type})")
            return False
    
    def handle_market_event(self, entry: Dict[str, Any]) -> bool:
        """
        Handle a Market journal event - triggers cargo update for Fleet Carriers
        
        :param entry: The journal entry data
        :return: True if processed as Fleet Carrier, False otherwise
        """
        if entry.get('StationType') != 'FleetCarrier':
            return False
        
        market_id = entry.get('MarketID')
        
        # Only process if this is a linked FC
        if market_id not in self.linked_fcs:
            logger.debug(f"Market event for unlinked FC {market_id} - ignoring")
            return False
        
        # Check stealth mode
        if self.stealth_mode:
            logger.debug(f"Market event for FC {market_id} - stealth mode enabled, ignoring")
            return False
        
        logger.info(f"Market event for linked FC {market_id} - updating cargo")
        self._update_fc_from_market(market_id)
        return True
    
    def handle_marketbuy_event(self, entry: Dict[str, Any]) -> bool:
        """
        Handle a MarketBuy journal event - player bought from FC
        
        :param entry: The journal entry data
        :return: True if processed as Fleet Carrier purchase, False otherwise
        """
        if self.current_station_type != 'FleetCarrier':
            return False
        
        market_id = entry.get('MarketID')
        commodity = entry.get('Type')
        count = entry.get('Count', 0)
        
        # Only process if this is a linked FC
        if market_id not in self.linked_fcs:
            logger.debug(f"MarketBuy for unlinked FC {market_id} - ignoring")
            return False
        
        # Check stealth mode
        if self.stealth_mode:
            logger.debug(f"MarketBuy for FC {market_id} - stealth mode enabled, ignoring")
            return False
        
        logger.info(f"Buying {count}x {commodity} from FC {market_id}")
        
        # Buying from FC reduces FC cargo (negative supply)
        cargo_diff = {commodity: -count}
        self._supply_fc_async(market_id, cargo_diff)
        return True
    
    def handle_marketsell_event(self, entry: Dict[str, Any]) -> bool:
        """
        Handle a MarketSell journal event - player sold to FC
        
        :param entry: The journal entry data
        :return: True if processed as Fleet Carrier sale, False otherwise
        """
        if self.current_station_type != 'FleetCarrier':
            return False
        
        market_id = entry.get('MarketID')
        commodity = entry.get('Type')
        count = entry.get('Count', 0)
        
        # Only process if this is a linked FC
        if market_id not in self.linked_fcs:
            logger.debug(f"MarketSell for unlinked FC {market_id} - ignoring")
            return False
        
        # Check stealth mode
        if self.stealth_mode:
            logger.debug(f"MarketSell for FC {market_id} - stealth mode enabled, ignoring")
            return False
        
        logger.info(f"Selling {count}x {commodity} to FC {market_id}")
        
        # Selling to FC increases FC cargo (positive supply)
        cargo_diff = {commodity: count}
        self._supply_fc_async(market_id, cargo_diff)
        return True
    
    def handle_cargotransfer_event(self, entry: Dict[str, Any]) -> bool:
        """
        Handle a CargoTransfer journal event - transfers between ship/carrier/SRV
        
        :param entry: The journal entry data
        :return: True if processed as Fleet Carrier transfer, False otherwise
        """
        logger.debug(f"handle_cargotransfer_event: current_station_type={self.current_station_type}, current_market_id={self.current_market_id}")
        
        if self.current_station_type != 'FleetCarrier':
            logger.debug(f"Not at a Fleet Carrier, ignoring CargoTransfer")
            return False
        
        market_id = self.current_market_id
        logger.debug(f"Checking if FC {market_id} is linked: {market_id in self.linked_fcs}")
        logger.debug(f"Linked FCs: {list(self.linked_fcs.keys())}")
        
        if market_id not in self.linked_fcs:
            logger.debug(f"FC {market_id} not in linked FCs")
            return False
        
        # Check stealth mode
        if self.stealth_mode:
            logger.debug(f"CargoTransfer for FC {market_id} - stealth mode enabled, ignoring")
            return False
        
        transfers = entry.get('Transfers', [])
        cargo_diff = {}
        
        for transfer in transfers:
            direction = transfer.get('Direction')
            commodity = transfer.get('Type')
            count = transfer.get('Count', 0)
            
            # Direction "tocarrier" means moving to FC (increase FC cargo)
            # Direction "toship" means moving from FC to ship (decrease FC cargo)
            if direction == 'tocarrier':
                cargo_diff[commodity] = cargo_diff.get(commodity, 0) + count
                logger.debug(f"Transfer {count}x {commodity} to FC")
            elif direction == 'toship':
                cargo_diff[commodity] = cargo_diff.get(commodity, 0) - count
                logger.debug(f"Transfer {count}x {commodity} from FC")
        
        if cargo_diff:
            logger.info(f"Cargo transfer for FC {market_id}: {cargo_diff}")
            self._supply_fc_async(market_id, cargo_diff)
            return True
        
        return False
    
    def _update_fc_from_market(self, market_id: int):
        """Update FC cargo based on current market data"""
        try:
            # Get current FC data from server
            fc_data = self.api_client.api_client.get_fc(market_id)
            if not fc_data:
                logger.error(f"Failed to get FC data for {market_id}")
                return
            
            # Get current market data from EDMC
            market_data = self._get_market_data()
            if not market_data:
                logger.warning(f"No market data available for FC {market_id}")
                return
            
            # Compare market data with server data and update discrepancies
            new_cargo = {}
            server_cargo = fc_data.get('cargo', {})
            
            for item in market_data:
                commodity_name = item.get('name', '')
                stock = item.get('stock', 0)
                is_producer = item.get('producer', False)
                is_consumer = item.get('consumer', False)
                
                # Strip localization suffix if present
                if commodity_name.endswith('_name;'):
                    commodity_name = commodity_name[1:-6]  # Remove $ and _name;
                
                # Update if producer with different stock, or non-producer/non-consumer with stock change
                if (is_producer and server_cargo.get(commodity_name, 0) != stock) or \
                   (not is_producer and not is_consumer and stock != server_cargo.get(commodity_name, 0)):
                    new_cargo[commodity_name] = stock
            
            if new_cargo:
                logger.info(f"Updating FC {market_id} cargo with {len(new_cargo)} changes")
                self._update_fc_cargo_async(market_id, new_cargo)
            else:
                logger.debug(f"No cargo changes needed for FC {market_id}")
                
        except Exception as e:
            logger.error(f"Failed to update FC from market: {e}", exc_info=True)
    
    def _get_market_data(self) -> Optional[List[Dict[str, Any]]]:
        """Get market data from EDMC"""
        try:
            # EDMC provides market data through the plugin system
            # This will need to be integrated with your main plugin's market data access
            if hasattr(self.api_client, 'get_market_data'):
                return self.api_client.get_market_data()
            else:
                logger.warning("No market data access method available")
                return None
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            return None
    
    def update_fc_cargo_from_capi(self, market_id: int, cargo_totals: Dict[str, int]):
        """
        Update FC cargo using data from Frontier CAPI.
        CAPI data significantly lags real-time, so we only use it for the initial 
        snapshot on plugin load. After that, we rely on real-time journal events.
        
        :param market_id: Fleet Carrier market ID
        :param cargo_totals: Dictionary of commodity name -> total quantity
        """
        # Check if we've already received CAPI data for this FC this session
        if market_id in self.capi_received_fcs:
            logger.info(f"Ignoring CAPI data for FC {market_id} - already received initial snapshot, using real-time journal events instead")
            return
        
        logger.info(f"Receiving initial CAPI snapshot for FC {market_id}")
        logger.debug(f"CAPI cargo totals: {cargo_totals}")
        
        # Mark this FC as having received CAPI data
        self.capi_received_fcs.add(market_id)
        
        # Update server with full cargo snapshot (initial state only)
        self._update_fc_cargo_async(market_id, cargo_totals)
    
    def _supply_fc_async(self, market_id: int, cargo_diff: Dict[str, int]):
        """Update FC cargo incrementally using the API queue"""
        self.api_client.queue_api_call(self._supply_fc, market_id, cargo_diff)
    
    def _supply_fc(self, market_id: int, cargo_diff: Dict[str, int]) -> bool:
        """Update FC cargo incrementally"""
        try:
            result = self.api_client.api_client.supply_fc(market_id, cargo_diff)
            if result:
                # Update local cache
                if market_id in self.linked_fcs:
                    self.linked_fcs[market_id]['cargo'] = result
                logger.info(f"Successfully updated FC {market_id} cargo")
                return True
            else:
                logger.error(f"Failed to update FC {market_id} cargo")
                return False
        except Exception as e:
            logger.error(f"Exception updating FC cargo: {e}", exc_info=True)
            return False
    
    def _update_fc_cargo_async(self, market_id: int, cargo: Dict[str, int]):
        """Replace entire FC cargo manifest using the API queue"""
        self.api_client.queue_api_call(self._update_fc_cargo, market_id, cargo)
    
    def _update_fc_cargo(self, market_id: int, cargo: Dict[str, int]) -> bool:
        """Replace entire FC cargo manifest"""
        try:
            result = self.api_client.api_client.update_fc_cargo(market_id, cargo)
            if result:
                # Update local cache
                if market_id in self.linked_fcs:
                    self.linked_fcs[market_id]['cargo'] = result
                logger.info(f"Successfully replaced FC {market_id} cargo")
                return True
            else:
                logger.error(f"Failed to replace FC {market_id} cargo")
                return False
        except Exception as e:
            logger.error(f"Exception replacing FC cargo: {e}", exc_info=True)
            return False
    
    def get_linked_fc_summary(self) -> str:
        """Get a summary of linked Fleet Carriers"""
        if not self.linked_fcs:
            return "No linked Fleet Carriers"
        
        total_cargo = {}
        for fc in self.linked_fcs.values():
            fc_cargo = fc.get('cargo', {})
            for commodity, count in fc_cargo.items():
                total_cargo[commodity] = total_cargo.get(commodity, 0) + count
        
        summary = f"Linked Fleet Carriers: {len(self.linked_fcs)}\n"
        summary += f"Total Commodities: {len(total_cargo)}\n"
        if total_cargo:
            summary += "Cargo Summary:\n"
            for commodity, count in sorted(total_cargo.items()):
                if count > 0:
                    summary += f"  {commodity}: {count}\n"
        
        return summary
