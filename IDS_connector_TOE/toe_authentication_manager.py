# ================================================================================
# toe_authentication_manager.py
# ================================================================================
"""
TOE Authentication Manager
---------------------------
Handles wallet-driven registration, SSI credential polling, and OAuth2 token
acquisition for the IDS-TOE component.  Modelled after SDT Manager's
SDTAuthenticationManager but designed as a standalone, in-memory module
(no SQLite dependency).

Flow (called during IDS-TOE startup):
  1. Register IDS-TOE via wallet controller  ->  POST /wallet/digital-twins
  2. Poll AM until status == "issued"        ->  GET  /api/digital-twins/<toe_id>
  3. Fetch OAuth2 access token               ->  POST /oauth/token (Basic Auth)
  4. Store credentials in memory on the manager instance
"""

import os
import time
import uuid
import logging
import threading
import requests
from typing import Optional, Dict, Tuple

LOGGER = logging.getLogger(__name__)


class TOEAuthenticationManager:
    """Manages registration, token acquisition, and credential storage for IDS-TOE."""

    def __init__(
        self,
        am_base_url: Optional[str] = None,
        wallet_controller_url: Optional[str] = None,
        wallet_controller_key: Optional[str] = None,
        digital_twin_api_key: Optional[str] = None,
        twin_owner: str = "ids-toe",
        twin_scope: str = "digital_twin profile",
        poll_interval: int = 5,
        poll_timeout: int = 180,
        verify_ssl: bool = False,
    ):
        """
        Initialize the TOE Authentication Manager.

        All URL / key parameters fall back to environment variables when not
        provided explicitly.

        Args:
            am_base_url:           Base URL for the Authentication Manager.
            wallet_controller_url: URL for the Wallet Controller.
            wallet_controller_key: API key for the Wallet Controller.
            digital_twin_api_key:  API key for the Digital Twin AM endpoint.
            twin_owner:            Owner label for the registered twin.
            twin_scope:            OAuth scope string.
            poll_interval:         Seconds between AM status polls.
            poll_timeout:          Max seconds to wait for credential issuance.
            verify_ssl:            Whether to verify TLS certificates.
        """
        # Configuration from args -> env -> defaults
        self.am_base_url = (
            am_base_url
            or os.environ.get("AM_BASE_URL", "http://iam.cobalt.local:3100")
        )
        self.wallet_controller_url = (
            wallet_controller_url
            or os.environ.get("WALLET_CONTROLLER_URL", "http://iam.cobalt.local:3200")
        )
        self.wallet_controller_key = (
            wallet_controller_key
            or os.environ.get("WALLET_CONTROLLER_KEY", "atestkeytoremotelycontrolthewallet")
        )
        self.digital_twin_api_key = (
            digital_twin_api_key
            or os.environ.get("DIGITAL_TWIN_API_KEY", "IvPBXYOesvseJQ3u0mwLPFgvN3Ugy2-P35aW2WlSUvQ")
        )
        self.twin_owner = twin_owner
        self.twin_scope = twin_scope
        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout
        self.verify_ssl = verify_ssl

        # In-memory credential store
        self._credentials: Dict[str, Optional[str]] = {
            "toe_id": None,
            "client_id": None,
            "client_secret": None,
            "access_token": None,
            "token_scope": twin_scope,
            "status": "pending",        # pending -> registered -> issued
        }
        self._lock = threading.Lock()

        LOGGER.info(
            "TOE Authentication Manager initialized "
            f"(AM={self.am_base_url}, Wallet={self.wallet_controller_url})"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_and_get_token(
        self,
        toe_id: Optional[str] = None,
        twin_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Full registration + token flow for the IDS-TOE component.

        If no toe_id is provided, a random hex identifier is generated.

        Args:
            toe_id:    Hexadecimal identifier for the TOE (auto-generated if None).
            twin_name: Human-readable name (defaults to "IDS-TOE-<toe_id>").

        Returns:
            (success: bool, access_token: str | None)
        """
        toe_id = toe_id or uuid.uuid4().hex[:8]
        twin_name = twin_name or f"IDS-TOE-{toe_id}"

        LOGGER.info(f"Starting authentication flow for IDS-TOE {toe_id}")

        # Step 1 — Register via wallet controller
        client_id, client_secret = self._register_twin(toe_id, twin_name)
        if not client_id or not client_secret:
            LOGGER.error(f"Registration failed for IDS-TOE {toe_id}")
            return False, None

        # Persist client credentials in memory
        with self._lock:
            self._credentials["toe_id"] = toe_id
            self._credentials["client_id"] = client_id
            self._credentials["client_secret"] = client_secret
            self._credentials["status"] = "registered"

        # Step 2 — Poll AM until credential is issued
        if not self._poll_until_issued(toe_id):
            LOGGER.error(f"Credential issuance timed out for IDS-TOE {toe_id}")
            return False, None

        # Step 3 — Fetch OAuth2 token
        access_token = self._fetch_token(client_id, client_secret)
        if not access_token:
            LOGGER.error(f"Token acquisition failed for IDS-TOE {toe_id}")
            return False, None

        # Step 4 — Store token in memory
        with self._lock:
            self._credentials["access_token"] = access_token
            self._credentials["status"] = "issued"

        LOGGER.info(f"Authentication flow completed for IDS-TOE {toe_id}")
        return True, access_token

    def get_access_token(self) -> Optional[str]:
        """
        Retrieve the stored access token.

        Returns:
            The access token string, or None if not yet acquired.
        """
        with self._lock:
            return self._credentials.get("access_token")

    def get_toe_id(self) -> Optional[str]:
        """
        Retrieve the TOE identifier used for registration.

        Returns:
            The hex identifier string, or None.
        """
        with self._lock:
            return self._credentials.get("toe_id")

    def get_credentials(self) -> Dict:
        """
        Retrieve a copy of the full credential dictionary.

        Returns:
            Dict with keys: toe_id, client_id, client_secret,
            access_token, token_scope, status.
        """
        with self._lock:
            return self._credentials.copy()

    def get_auth_status(self) -> str:
        """
        Retrieve the current authentication status.

        Returns:
            One of: 'pending', 'registered', 'issued', 'failed'.
        """
        with self._lock:
            return self._credentials.get("status", "pending")

    # ------------------------------------------------------------------
    # Internal helpers (mirror SDTAuthenticationManager logic)
    # ------------------------------------------------------------------

    def _register_twin(
        self, toe_id: str, twin_name: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Register the IDS-TOE with the wallet controller.

        Returns:
            (client_id, client_secret) or (None, None) on failure.
        """
        url = f"{self.wallet_controller_url}/wallet/digital-twins"
        payload = {
            "twin_id": toe_id,
            "name": twin_name,
            "owner": self.twin_owner,
            "scope": self.twin_scope,
        }
        headers = {
            "X-Api-Key": self.wallet_controller_key,
            "Content-Type": "application/json",
        }

        try:
            LOGGER.info(f"Registering IDS-TOE {toe_id} with wallet controller")
            response = requests.post(
                url, json=payload, headers=headers,
                timeout=30, verify=self.verify_ssl,
            )
            response.raise_for_status()

            data = response.json()
            registration = data.get("registration", data)
            client_info = registration.get("client", {})
            client_id = client_info.get("client_id")
            client_secret = client_info.get("client_secret")

            if not client_id or not client_secret:
                LOGGER.error(
                    f"Wallet response missing client credentials: {data}"
                )
                return None, None

            LOGGER.info(
                f"IDS-TOE {toe_id} registered — client_id={client_id}"
            )
            return client_id, client_secret

        except requests.exceptions.HTTPError as e:
            LOGGER.error(
                f"Wallet registration HTTP {e.response.status_code}: "
                f"{e.response.text}"
            )
        except requests.exceptions.RequestException as e:
            LOGGER.error(f"Wallet registration request failed: {e}")

        return None, None

    def _poll_until_issued(self, toe_id: str) -> bool:
        """
        Poll the AM until the twin credential status is 'issued'.

        Returns:
            True if issued within the timeout.
        """
        url = f"{self.am_base_url}/api/digital-twins/{toe_id}"
        headers = {"X-Api-Key": self.digital_twin_api_key}
        start = time.time()
        attempt = 0

        LOGGER.info(f"Polling AM for credential issuance (IDS-TOE {toe_id})")

        while time.time() - start < self.poll_timeout:
            attempt += 1
            try:
                response = requests.get(
                    url, headers=headers,
                    timeout=10, verify=self.verify_ssl,
                )
                response.raise_for_status()
                status = response.json().get("status", "unknown")
                elapsed = int(time.time() - start)

                LOGGER.info(
                    f"IDS-TOE {toe_id} credential status: {status} "
                    f"(attempt {attempt}, {elapsed}s elapsed)"
                )

                if status == "issued":
                    LOGGER.info(f"Credential issued for IDS-TOE {toe_id}")
                    return True
                if status == "failed":
                    LOGGER.error(f"Credential issuance failed for IDS-TOE {toe_id}")
                    with self._lock:
                        self._credentials["status"] = "failed"
                    return False

            except requests.exceptions.RequestException as e:
                LOGGER.warning(f"Poll attempt {attempt} failed: {e}")

            # Simple back-off: after 10 attempts double the interval
            interval = self.poll_interval if attempt <= 10 else self.poll_interval * 2
            time.sleep(interval)

        LOGGER.error(
            f"Credential polling timed out for IDS-TOE {toe_id} "
            f"after {self.poll_timeout}s"
        )
        with self._lock:
            self._credentials["status"] = "failed"
        return False

    def _fetch_token(
        self, client_id: str, client_secret: str
    ) -> Optional[str]:
        """
        Fetch an OAuth2 access token using client credentials.

        Returns:
            The access token string, or None.
        """
        url = f"{self.am_base_url}/oauth/token"
        data = {
            "grant_type": "client_credentials",
            "scope": self.twin_scope,
        }

        try:
            LOGGER.info("Requesting OAuth2 token from AM")
            response = requests.post(
                url,
                auth=(client_id, client_secret),
                data=data,
                timeout=10,
                verify=self.verify_ssl,
            )
            response.raise_for_status()

            token_data = response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                LOGGER.error("AM response did not contain an access_token")
                return None

            LOGGER.info("OAuth2 token acquired successfully")
            return access_token

        except requests.exceptions.RequestException as e:
            LOGGER.error(f"Token request failed: {e}")
            return None