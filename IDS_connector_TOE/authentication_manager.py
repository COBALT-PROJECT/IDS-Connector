"""
Authentication Manager JWT client.

Fetches an OAuth2 client-credentials JWT from the Authentication Manager and
stores it through AuthTokenStore.
"""
import logging
from typing import Dict, Optional

import requests

from auth_token_store import AuthTokenStore


logger = logging.getLogger(__name__)


class AuthenticationManager:
    """Fetch and use JWTs from the external Authentication Manager."""

    def __init__(
        self,
        auth_base_url: str = "http://iam.cobalt.local:3100",
        client_id: str = "idstoe",
        client_secret: str = "3061426b1ae5a36de114580e30f860475e3b9dcc91d15baf125a30cd8c9b7330",
        scope: str = "digital_twins profile",
        request_timeout: int = 30,
        token_store: Optional[AuthTokenStore] = None,
        token_validation_path: str = "/oauth/userinfo",
    ):
        self.auth_base_url = auth_base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.request_timeout = request_timeout
        self.token_store = token_store or AuthTokenStore()
        self.token_validation_path = (
            token_validation_path
            if token_validation_path.startswith("/")
            else f"/{token_validation_path}"
        )

        logger.info("AuthenticationManager initialized for %s", self.auth_base_url)

    def refresh_jwt(self) -> Dict:
        """
        Fetch a fresh JWT using client credentials and persist it.

        Equivalent curl:
          curl -X POST <auth_base_url>/oauth/token
            -H "Content-Type: application/x-www-form-urlencoded"
            -u "<client_id>:<client_secret>"
            -d "grant_type=client_credentials&scope=<scope>"
        """
        url = f"{self.auth_base_url}/oauth/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "scope": self.scope,
        }

        logger.info("Requesting JWT from Authentication Manager at %s", url)

        response = requests.post(
            url,
            headers=headers,
            auth=(self.client_id, self.client_secret),
            data=data,
            timeout=self.request_timeout,
        )
        response.raise_for_status()

        token_data = response.json()
        saved_token = self.token_store.save_token(token_data)
        logger.info("JWT stored successfully")

        return self._metadata_from_token(saved_token)

    def validate_jwt(self, token: str) -> Dict:
        """Validate a caller JWT using IAM's /oauth/userinfo endpoint."""
        if not token:
            return {"active": False}

        url = f"{self.auth_base_url}{self.token_validation_path}"
        response = requests.get(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
            timeout=self.request_timeout,
        )
        response.raise_for_status()

        result = response.json()
        if not isinstance(result, dict):
            return {"active": False}

        status = result.get("status")
        result["active"] = status in ("active", "issued")
        return result

    def get_token(self) -> Optional[str]:
        token = self.token_store.get_token()
        return token.get("access_token") if token else None

    def get_token_metadata(self) -> Dict:
        metadata = self.token_store.get_token_metadata()
        if not metadata:
            return {"has_token": False}
        return metadata

    def get_authorization_header(self) -> Dict[str, str]:
        token = self.token_store.get_token()
        if not token:
            raise RuntimeError("No JWT is stored. Refresh the JWT first.")

        token_type = token.get("token_type") or "Bearer"
        return {"Authorization": f"{token_type} {token['access_token']}"}

    def authenticated_request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict] = None,
    ) -> Dict:
        """Call the Authentication Manager using the stored JWT."""
        method = method.upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError("Unsupported HTTP method")

        if not path.startswith("/"):
            path = f"/{path}"

        url = f"{self.auth_base_url}{path}"
        headers = self.get_authorization_header()
        headers["Accept"] = "application/json"

        response = requests.request(
            method,
            url,
            headers=headers,
            json=payload,
            timeout=self.request_timeout,
        )

        result = {
            "status_code": response.status_code,
            "url": url,
        }

        try:
            result["response"] = response.json()
        except ValueError:
            result["response"] = response.text

        return result

    def _metadata_from_token(self, token: Dict) -> Dict:
        return {
            "has_token": True,
            "token_type": token.get("token_type"),
            "scope": token.get("scope"),
            "expires_in": token.get("expires_in"),
            "created_at": token.get("created_at"),
            "expires_at": token.get("expires_at"),
        }
