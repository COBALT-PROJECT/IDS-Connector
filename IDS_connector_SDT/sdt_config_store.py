# ================================================================================
# sdt_config_store.py
# ================================================================================
"""
SDT Config Store - Singleton shared configuration store for the ids-sdt component.
Holds the SDT registration payload received via POST /api/IDSconnector/SDT/config
and makes it accessible to all modules without circular imports.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SDTConfigStore:
    """
    Singleton store that holds the SDT configuration received from the
    registration endpoint. All modules import this instance directly.

    Usage (in any module):
        from sdt_config_store import sdt_config
        client_id = sdt_config.get("client_id")
    """

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._registered_at: Optional[datetime] = None
        self._is_configured: bool = False

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def set(self, payload: Dict[str, Any]) -> None:
        """
        Populate the store from the registration payload.
        Flattens the top-level fields and keeps 'components' as a nested dict.

        Expected payload shape:
        {
            "sdt_id":       str,
            "client_id":    str,
            "client_secret": str,
            "access_token": str,
            "components": {
                "sdt":           str,
                "ids_connector": str,
                "watchtower":    str
            }
        }
        """
        self._store = {
            "sdt_id":        payload.get("sdt_id"),
            "client_id":     payload.get("client_id"),
            "client_secret": payload.get("client_secret"),
            "access_token":  payload.get("access_token"),
            "components":    payload.get("components", {}),
        }
        self._registered_at = datetime.now()
        self._is_configured = True
        logger.info(
            f"SDTConfigStore updated — sdt_id={self._store['sdt_id']}, "
            f"components={list(self._store['components'].keys())}"
        )

    def clear(self) -> None:
        """Reset the store to its empty state."""
        self._store = {}
        self._registered_at = None
        self._is_configured = False
        logger.info("SDTConfigStore cleared")

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Return a top-level value by key."""
        return self._store.get(key, default)

    def get_component(self, component_name: str, default: Any = None) -> Any:
        """Return a single component ID by name (e.g. 'ids_connector')."""
        return self._store.get("components", {}).get(component_name, default)

    def all(self) -> Dict[str, Any]:
        """Return a shallow copy of the entire store."""
        return dict(self._store)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def is_configured(self) -> bool:
        """True once a valid payload has been stored."""
        return self._is_configured

    @property
    def registered_at(self) -> Optional[datetime]:
        """Timestamp of the last successful registration."""
        return self._registered_at

    def status(self) -> Dict[str, Any]:
        """Return a safe status summary (secrets redacted)."""
        if not self._is_configured:
            return {"configured": False}
        return {
            "configured":     True,
            "registered_at":  self._registered_at.isoformat() if self._registered_at else None,
            "sdt_id":         self._store.get("sdt_id"),
            "client_id":      self._store.get("client_id"),
            "client_secret":  "***redacted***",
            "access_token":   "***redacted***",
            "components":     self._store.get("components", {}),
        }


# ---------------------------------------------------------------------------
# Module-level singleton — import this instance everywhere
# ---------------------------------------------------------------------------
sdt_config = SDTConfigStore()