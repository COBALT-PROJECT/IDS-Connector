# ================================================================================
# resource_state_store.py
# ================================================================================
"""
Resource State Store - tracks the real sync status of each connector resource.

Replaces the old "time-based cache" model (a resource was hidden once it had
merely been *handed out* once, and reappeared again after a TTL expired
regardless of whether anything actually happened to it) with a state-based
model: a resource is only ever hidden once SDT has *confirmed* it was
ingested. There is no time-based expiry of "freshness" at all — a resource
stays AVAILABLE for as long as it takes to actually get synced.

States
------
AVAILABLE (implicit/default, untracked) -> DELIVERED -> CONFIRMED   (terminal)
                                                       -> AVAILABLE  (retry, on
                                                          reported failure)
                                                       -> DEAD       (terminal,
                                                          after max attempts)
DELIVERED -> AVAILABLE automatically if no confirm call arrives within
             DELIVERY_TIMEOUT_SECONDS (SDT crashed mid-ingest, or the confirm
             HTTP call itself got dropped) - a resource can never be stuck
             forever just because nobody told us what happened to it.

Persistence
-----------
State is persisted as JSON to STATE_FILE so a pod restart does not forget
which resources were already confirmed (otherwise every restart would
re-offer, and SDT would re-ingest, everything ever synced). If STATE_FILE
is unwritable, the store logs loudly and keeps serving from memory rather
than crashing the service - degraded persistence, not a dead connector.
"""
import json
import logging
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

AVAILABLE = "available"
DELIVERED = "delivered"
CONFIRMED = "confirmed"
DEAD = "dead"

# Outcomes SDT can report back via POST /api/IDSconnector/confirm.
# created/updated/skipped all mean "SDT is done with this, don't offer it
# again" - skipped covers both a true duplicate (identical content already
# in Ditto) and a resource we deliberately superseded ourselves (see
# confirm_superseded below).
TERMINAL_OUTCOMES = {"created", "updated", "skipped"}
RETRYABLE_OUTCOMES = {"failed"}
VALID_OUTCOMES = TERMINAL_OUTCOMES | RETRYABLE_OUTCOMES


class ResourceStateStore:
    """
    Thread-safe, disk-persisted state machine for connector resource sync
    status. See module docstring for the state diagram.
    """

    def __init__(self, state_file: Optional[str], max_attempts: int = 5,
                 delivery_timeout_seconds: int = 120):
        self.state_file = state_file
        self.max_attempts = max_attempts
        self.delivery_timeout_seconds = delivery_timeout_seconds
        self._lock = threading.RLock()
        self._resources: Dict[str, dict] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self):
        if not self.state_file:
            logger.warning("No STATE_FILE configured - resource sync state will NOT survive a restart")
            return
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                self._resources = data.get("resources", {})
                logger.info(
                    f"Loaded resource sync state: {len(self._resources)} tracked "
                    f"resource(s) from {self.state_file}"
                )
            else:
                logger.info(f"No existing state file at {self.state_file} - starting with empty state")
        except Exception as e:
            logger.error(
                f"Failed to load resource sync state from {self.state_file}: {e} "
                f"- starting empty (previously confirmed resources may be re-offered once)"
            )
            self._resources = {}

    def _save(self):
        if not self.state_file:
            return
        try:
            state_dir = os.path.dirname(self.state_file)
            if state_dir:
                os.makedirs(state_dir, exist_ok=True)
            tmp_path = f"{self.state_file}.tmp"
            with open(tmp_path, "w") as f:
                json.dump({"resources": self._resources}, f, indent=2)
            os.replace(tmp_path, self.state_file)
        except Exception as e:
            # Fail open: keep serving from memory even if the volume is
            # unwritable. Loud on purpose - it means state won't survive
            # the next restart.
            logger.error(f"Failed to persist resource sync state to {self.state_file}: {e}")

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_state(self, resource_id: str) -> str:
        with self._lock:
            entry = self._resources.get(resource_id)
            return entry["state"] if entry else AVAILABLE

    def is_available(self, resource_id: str) -> bool:
        return self.get_state(resource_id) == AVAILABLE

    def get_entry(self, resource_id: str) -> Optional[dict]:
        with self._lock:
            entry = self._resources.get(resource_id)
            return dict(entry) if entry else None

    def get_ids_by_state(self, state: str) -> List[str]:
        """Return every tracked resource_id currently in the given state."""
        with self._lock:
            return [rid for rid, entry in self._resources.items() if entry.get("state") == state]

    def get_summary(self) -> Dict[str, int]:
        """Counts by state, for a diagnostics/reconciliation endpoint."""
        with self._lock:
            counts = {AVAILABLE: 0, DELIVERED: 0, CONFIRMED: 0, DEAD: 0}
            for entry in self._resources.values():
                counts[entry.get("state", AVAILABLE)] = counts.get(entry.get("state", AVAILABLE), 0) + 1
            return counts

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def sweep_expired_deliveries(self) -> List[str]:
        """
        Revert any DELIVERED resource that's been in flight longer than
        delivery_timeout_seconds back to AVAILABLE. Call this at the start
        of every get_data_request - it's what stops a crashed SDT or a
        dropped confirm call from stranding a resource forever.
        """
        reverted = []
        now = datetime.utcnow()
        with self._lock:
            for resource_id, entry in list(self._resources.items()):
                if entry.get("state") != DELIVERED:
                    continue
                delivered_at = entry.get("delivered_at")
                if not delivered_at:
                    continue
                try:
                    age = (now - datetime.fromisoformat(delivered_at)).total_seconds()
                except ValueError:
                    continue
                if age >= self.delivery_timeout_seconds:
                    logger.warning(
                        f"Resource {resource_id} stuck DELIVERED for {age:.0f}s "
                        f"(timeout {self.delivery_timeout_seconds}s) - reverting to AVAILABLE for retry"
                    )
                    entry["state"] = AVAILABLE
                    entry.pop("delivered_at", None)
                    entry["updated_at"] = now.isoformat()
                    reverted.append(resource_id)
            if reverted:
                self._save()
        return reverted

    def claim_available(self, resource_ids: List[str]) -> List[str]:
        """
        Atomically select the subset of resource_ids that are currently
        AVAILABLE and mark them DELIVERED in the same critical section, so
        two overlapping sync calls can never both claim the same resource.

        Returns the subset actually claimed (already-delivered/confirmed/
        dead resources are silently skipped).
        """
        if not resource_ids:
            return []
        now_iso = datetime.utcnow().isoformat()
        claimed = []
        with self._lock:
            for resource_id in resource_ids:
                entry = self._resources.get(resource_id)
                if entry is not None and entry.get("state") != AVAILABLE:
                    continue  # already delivered/confirmed/dead
                entry = entry or {"attempts": 0}
                entry["state"] = DELIVERED
                entry["delivered_at"] = now_iso
                entry["updated_at"] = now_iso
                self._resources[resource_id] = entry
                claimed.append(resource_id)
            if claimed:
                self._save()
        if claimed:
            logger.info(f"Claimed {len(claimed)} resource(s) as DELIVERED: {claimed}")
        return claimed

    def confirm(self, resource_id: str, outcome: str) -> str:
        """
        Apply SDT's reported ingestion outcome for one resource.

        outcome: "created" | "updated" | "skipped" | "failed"
        Returns the resulting state (CONFIRMED, AVAILABLE, or DEAD).
        """
        if outcome not in VALID_OUTCOMES:
            logger.warning(f"Unrecognized confirm outcome '{outcome}' for {resource_id} - treating as 'failed'")
            outcome = "failed"

        now_iso = datetime.utcnow().isoformat()
        with self._lock:
            entry = self._resources.get(resource_id, {"attempts": 0})

            if outcome in TERMINAL_OUTCOMES:
                entry["state"] = CONFIRMED
                entry["last_outcome"] = outcome
                entry["updated_at"] = now_iso
                entry.pop("delivered_at", None)
                self._resources[resource_id] = entry
                self._save()
                logger.info(f"Resource {resource_id} CONFIRMED (outcome={outcome})")
                return CONFIRMED

            # outcome == "failed"
            attempts = entry.get("attempts", 0) + 1
            entry["attempts"] = attempts
            entry["last_outcome"] = outcome
            entry["updated_at"] = now_iso
            entry.pop("delivered_at", None)

            if attempts >= self.max_attempts:
                entry["state"] = DEAD
                self._resources[resource_id] = entry
                self._save()
                logger.error(f"Resource {resource_id} marked DEAD after {attempts} failed attempt(s)")
                return DEAD

            entry["state"] = AVAILABLE
            self._resources[resource_id] = entry
            self._save()
            logger.warning(
                f"Resource {resource_id} ingestion failed (attempt {attempts}/{self.max_attempts}) "
                f"- back to AVAILABLE for retry"
            )
            return AVAILABLE

    def confirm_superseded(self, resource_id: str):
        """
        Mark an older duplicate as confirmed directly - it's superseded by a
        newer resource sharing the same (toe_id, filename) and must never be
        offered or retried on its own.
        """
        self.confirm(resource_id, "skipped")

    def reset_all(self) -> int:
        """
        Operator escape hatch: forget all tracked state. Every CONFIRMED/DEAD
        resource becomes AVAILABLE again and will be re-offered (SDT's own
        content-based dedupe will generally no-op them straight back to
        'skipped'). Used by the legacy /clear-cache endpoint.
        """
        with self._lock:
            count = len(self._resources)
            self._resources = {}
            self._save()
        logger.warning(f"Resource sync state reset - {count} tracked resource(s) forgotten")
        return count


def _build_default_store() -> ResourceStateStore:
    state_file = os.environ.get("STATE_FILE", "/data/resource_sync_state.json")
    max_attempts = int(os.environ.get("MAX_DELIVERY_ATTEMPTS", "5"))
    delivery_timeout = int(os.environ.get("DELIVERY_TIMEOUT_SECONDS", "120"))
    return ResourceStateStore(state_file, max_attempts=max_attempts, delivery_timeout_seconds=delivery_timeout)


# Module-level singleton - import this instance everywhere, mirroring the
# sdt_config_store.py pattern already used in this service.
resource_state = _build_default_store()
