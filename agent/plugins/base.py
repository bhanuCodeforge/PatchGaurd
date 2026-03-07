from abc import ABC, abstractmethod
from typing import List, Dict, Any

class OSPlugin(ABC):
    """
    Abstract base class for OS-specific patch management plugins.
    """
    @abstractmethod
    def get_system_info(self) -> Dict[str, Any]:
        """Return basic hardware and OS metadata."""
        pass

    @abstractmethod
    def scan_patches(self) -> List[Dict[str, Any]]:
        """Scan the system for missing patches and return a list of patch data."""
        pass

    @abstractmethod
    def install_patch(self, patch_id: str) -> bool:
        """Install a specific patch by ID or name."""
        pass

    @abstractmethod
    def get_inventory(self) -> Dict[str, Any]:
        """Collect detailed hardware and software inventory."""
        pass

    @abstractmethod
    def reboot(self) -> bool:
        """Trigger a system reboot."""
        pass
