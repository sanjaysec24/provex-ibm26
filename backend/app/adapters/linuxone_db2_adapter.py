from typing import Any, Dict, List
from app.adapters.base import AdapterError, DataSourceAdapter


class LinuxOneDb2Adapter(DataSourceAdapter):
    """
    Placeholder adapter for IBM LinuxONE / Db2 on IBM Z integration.
    
    STATUS: UNIMPLEMENTED (STUB ONLY)
    This placeholder adheres to the DataSourceAdapter interface.
    No live IBM infrastructure connection, credentials, or network calls are active.
    It intentionally raises NotImplementedError to prevent false claims of live integration.
    """

    def __init__(self, host: str = "linuxone.internal.stub", port: int = 50000) -> None:
        self.host = host
        self.port = port
        self._connected = False

    def is_connected(self) -> bool:
        """Explicitly false: no live IBM connection is established."""
        return False

    def list_records(self, resource: str, limit: int = 10) -> List[Dict[str, Any]]:
        raise NotImplementedError(
            "IBM LinuxONE / Db2 live adapter is not implemented or connected. "
            "Use MockSyntheticAdapter for offline execution."
        )

    def get_record_by_id(self, resource: str, record_id: str) -> Dict[str, Any]:
        raise NotImplementedError(
            "IBM LinuxONE / Db2 live adapter is not implemented or connected. "
            "Use MockSyntheticAdapter for offline execution."
        )
