from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AdapterError(Exception):
    """Base exception for data adapter errors."""
    pass


class InvalidResourceError(AdapterError):
    """Raised when an unknown or unsupported resource is requested."""
    pass


class RecordNotFoundError(AdapterError):
    """Raised when a specific record identifier cannot be found."""
    pass


class DataSourceAdapter(ABC):
    """
    Abstract interface for enterprise data source adapters.
    
    CRITICAL ARCHITECTURAL CONTRACT:
    The adapter is strictly an internal retrieval boundary. Raw data fetched by
    the adapter MUST NOT be exposed directly to untrusted clients or AI models.
    Every read must flow through the deterministic policy engine and data sanitizer.
    """

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if the underlying data store is reachable."""
        pass

    @abstractmethod
    def list_records(self, resource: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve raw records for an authorized resource. Internal use only."""
        pass

    @abstractmethod
    def get_record_by_id(self, resource: str, record_id: str) -> Dict[str, Any]:
        """Retrieve a specific raw record by unique identifier. Internal use only."""
        pass
