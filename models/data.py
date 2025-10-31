"""
Data models for Ravencolonial EDMC Plugin

Defines structured data classes for better type safety and validation.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class ProjectData:
    """Represents a colonization project"""
    build_id: str
    build_name: str
    system_address: int
    market_id: int
    system_name: str
    body_name: Optional[str] = None
    body_id: Optional[int] = None
    architect: Optional[str] = None
    build_type: Optional[str] = None
    is_primary: bool = False
    complete: bool = False
    discord_link: Optional[str] = None
    notes: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectData':
        """Create ProjectData from dictionary"""
        return cls(
            build_id=data.get('buildId', ''),
            build_name=data.get('buildName', ''),
            system_address=data.get('systemAddress', 0),
            market_id=data.get('marketId', 0),
            system_name=data.get('systemName', ''),
            body_name=data.get('bodyName'),
            body_id=data.get('bodyId'),
            architect=data.get('architect'),
            build_type=data.get('buildType'),
            is_primary=data.get('isPrimary', False),
            complete=data.get('complete', False),
            discord_link=data.get('discordLink'),
            notes=data.get('notes')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ProjectData to dictionary"""
        return {
            'buildId': self.build_id,
            'buildName': self.build_name,
            'systemAddress': self.system_address,
            'marketId': self.market_id,
            'systemName': self.system_name,
            'bodyName': self.body_name,
            'bodyId': self.body_id,
            'architect': self.architect,
            'buildType': self.build_type,
            'isPrimary': self.is_primary,
            'complete': self.complete,
            'discordLink': self.discord_link,
            'notes': self.notes
        }


@dataclass
class SystemSite:
    """Represents a pre-planned construction site in a system"""
    id: str
    name: str
    build_type: str
    system_address: int
    body_id: Optional[int] = None
    body_name: Optional[str] = None
    is_primary: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemSite':
        """Create SystemSite from dictionary"""
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            build_type=data.get('buildType', ''),
            system_address=data.get('systemAddress', 0),
            body_id=data.get('bodyId'),
            body_name=data.get('bodyName'),
            is_primary=data.get('isPrimary', False) or data.get('primary', False) or data.get('is_primary', False)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert SystemSite to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'buildType': self.build_type,
            'systemAddress': self.system_address,
            'bodyId': self.body_id,
            'bodyName': self.body_name,
            'isPrimary': self.is_primary
        }


@dataclass
class ConstructionDepotData:
    """Represents construction depot status from journal events"""
    market_id: int
    construction_progress: float
    construction_complete: bool
    construction_failed: bool
    resources_required: List[Dict[str, Any]]
    system_address: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConstructionDepotData':
        """Create ConstructionDepotData from dictionary"""
        return cls(
            market_id=data.get('MarketID', 0),
            construction_progress=data.get('ConstructionProgress', 0.0),
            construction_complete=data.get('ConstructionComplete', False),
            construction_failed=data.get('ConstructionFailed', False),
            resources_required=data.get('ResourcesRequired', []),
            system_address=data.get('SystemAddress')
        )
    
    def get_total_required(self) -> int:
        """Get total amount of all required resources"""
        return sum(r.get('RequiredAmount', 0) for r in self.resources_required)
    
    def get_total_provided(self) -> int:
        """Get total amount of all provided resources"""
        return sum(r.get('ProvidedAmount', 0) for r in self.resources_required)
    
    def get_still_needed(self) -> Dict[str, int]:
        """Get dictionary of resources still needed"""
        needed = {}
        for resource in self.resources_required:
            name = resource.get('Name', '').replace('$', '').replace('_name;', '').lower()
            required = resource.get('RequiredAmount', 0)
            provided = resource.get('ProvidedAmount', 0)
            still_needed = required - provided
            if name and still_needed > 0:
                needed[name] = still_needed
        return needed


@dataclass
class CargoContribution:
    """Represents a cargo contribution to a construction project"""
    commodity_name: str
    amount: int
    commander: str
    build_id: str
    timestamp: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CargoContribution':
        """Create CargoContribution from dictionary"""
        return cls(
            commodity_name=data.get('commodityName', ''),
            amount=data.get('amount', 0),
            commander=data.get('commander', ''),
            build_id=data.get('buildId', ''),
            timestamp=data.get('timestamp')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert CargoContribution to dictionary"""
        return {
            'commodityName': self.commodity_name,
            'amount': self.amount,
            'commander': self.commander,
            'buildId': self.build_id,
            'timestamp': self.timestamp
        }
