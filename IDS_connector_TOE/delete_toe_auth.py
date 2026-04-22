#!/usr/bin/env python3
# ================================================================================
# delete_toe_auth.py
# ================================================================================
"""
Standalone CLI utility to delete an IDS-TOE twin registration from the
Authentication Manager (wallet controller) and optionally revoke its
OAuth2 access token.

Usage:
    python delete_toe_auth.py <toe_id>
    python delete_toe_auth.py <toe_id> --token <access_token>
    python delete_toe_auth.py <toe_id> --am-url http://iam.cobalt.local:3100 
    python delete_toe_auth.py --list

Examples:
    # Delete twin registration only
    python delete_toe_auth.py a1b2c3d4 (USE THIS) #note: the access token expires naturally.

    # Delete twin registration and revoke the access token
    python delete_toe_auth.py a1b2c3d4 --token eyJhbGciOi... (WORKS, USE THIS)

    # List all registered digital twins on the AM
    python delete_toe_auth.py --list

    # Use custom URLs
    python delete_toe_auth.py a1b2c3d4 \\
        --wallet-url http://iam.cobalt.local:3200 \\
        --wallet-key atestkeytoremotelycontrolthewallet
"""

import argparse
import os
import sys
import logging
import requests
import urllib3

# Silence TLS warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def delete_from_wallet(toe_id: str, wallet_url: str, wallet_key: str,
                       verify_ssl: bool = False) -> bool:
    """
    Delete the twin registration from the wallet controller.

    DELETE /wallet/digital-twins/<toe_id>

    Returns True if deleted or already gone (404).
    """
    url = f"{wallet_url}/wallet/digital-twins/{toe_id}"
    headers = {"X-Api-Key": wallet_key}

    try:
        logger.info(f"Deleting twin {toe_id} from wallet controller at {url}")
        response = requests.delete(url, headers=headers, timeout=15,
                                   verify=verify_ssl)

        if response.status_code == 200:
            logger.info(f"Twin {toe_id} deleted successfully from wallet controller")
            return True
        elif response.status_code == 404:
            logger.warning(f"Twin {toe_id} not found in wallet — already deleted")
            return True
        else:
            logger.error(
                f"Wallet deletion failed — HTTP {response.status_code}: "
                f"{response.text}"
            )
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Wallet deletion request failed: {e}")
        return False


def revoke_token(access_token: str, am_url: str,
                 verify_ssl: bool = False) -> bool:
    """
    Attempt to revoke an OAuth2 access token via the AM's revocation
    endpoint.

    POST /oauth/revoke   (RFC 7009)

    If the AM does not expose a /oauth/revoke endpoint the call will
    fail gracefully — the token will simply expire on its own.
    """
    url = f"{am_url}/oauth/revoke"
    data = {
        "token": access_token,
        "token_type_hint": "access_token",
    }

    try:
        logger.info(f"Revoking access token via {url}")
        response = requests.post(url, data=data, timeout=10,
                                 verify=verify_ssl)

        if response.status_code in (200, 204):
            logger.info("Access token revoked successfully")
            return True
        elif response.status_code == 404:
            logger.warning(
                "AM does not expose /oauth/revoke — token will expire naturally"
            )
            return False
        else:
            logger.error(
                f"Token revocation failed — HTTP {response.status_code}: "
                f"{response.text}"
            )
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Token revocation request failed: {e}")
        return False


def list_twins(am_url: str, api_key: str,
               verify_ssl: bool = False) -> None:
    """
    List all registered digital twins on the AM.

    GET /api/digital-twins
    """
    url = f"{am_url}/api/digital-twins"
    headers = {"X-Api-Key": api_key}

    try:
        logger.info(f"Listing digital twins from {url}")
        response = requests.get(url, headers=headers, timeout=10,
                                verify=verify_ssl)

        if response.status_code == 200:
            twins = response.json()
            if isinstance(twins, list):
                if not twins:
                    print("No digital twins registered.")
                else:
                    print(f"{'ID':<20} {'Name':<30} {'Status':<12}")
                    print("-" * 62)
                    for twin in twins:
                        tid = twin.get("twin_id", twin.get("id", "?"))
                        name = twin.get("name", "?")
                        status = twin.get("status", "?")
                        print(f"{tid:<20} {name:<30} {status:<12}")
            else:
                print(response.json())
        else:
            logger.error(f"Failed to list twins — HTTP {response.status_code}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to list twins: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Delete an IDS-TOE twin registration from the "
                    "Authentication Manager / wallet controller.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "toe_id",
        nargs="?",
        help="Hexadecimal identifier of the IDS-TOE twin to delete",
    )
    parser.add_argument(
        "--token",
        help="OAuth2 access token to revoke (optional)",
    )
    parser.add_argument(
        "--am-url",
        default=os.environ.get("AM_BASE_URL", "http://iam.cobalt.local:3100"),
        help="Base URL for the Authentication Manager "
             "(default: $AM_BASE_URL or http://iam.cobalt.local:3100)",
    )
    parser.add_argument(
        "--wallet-url",
        default=os.environ.get("WALLET_CONTROLLER_URL", "http://iam.cobalt.local:3200"),
        help="URL for the Wallet Controller "
             "(default: $WALLET_CONTROLLER_URL or http://iam.cobalt.local:3200)",
    )
    parser.add_argument(
        "--wallet-key",
        default=os.environ.get("WALLET_CONTROLLER_KEY",
                               "atestkeytoremotelycontrolthewallet"),
        help="API key for the Wallet Controller "
             "(default: $WALLET_CONTROLLER_KEY)",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("DIGITAL_TWIN_API_KEY",
                               "IvPBXYOesvseJQ3u0mwLPFgvN3Ugy2-P35aW2WlSUvQ"),
        help="API key for the Digital Twin AM endpoint "
             "(default: $DIGITAL_TWIN_API_KEY)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_twins",
        help="List all registered digital twins on the AM and exit",
    )
    parser.add_argument(
        "--verify-ssl",
        action="store_true",
        default=False,
        help="Verify TLS certificates (default: disabled)",
    )

    args = parser.parse_args()

    # --list mode
    if args.list_twins:
        list_twins(args.am_url, args.api_key, args.verify_ssl)
        sys.exit(0)

    # Normal deletion mode — toe_id is required
    if not args.toe_id:
        parser.error("toe_id is required (or use --list to list twins)")

    print(f"{'='*60}")
    print(f"  Deleting IDS-TOE twin: {args.toe_id}")
    print(f"  Wallet Controller:     {args.wallet_url}")
    print(f"  Authentication Manager:{args.am_url}")
    print(f"{'='*60}")

    success = True

    # Step 1: Delete from wallet controller
    wallet_ok = delete_from_wallet(
        args.toe_id, args.wallet_url, args.wallet_key, args.verify_ssl
    )
    if not wallet_ok:
        success = False

    # Step 2: Revoke access token (if provided)
    if args.token:
        token_ok = revoke_token(args.token, args.am_url, args.verify_ssl)
        if not token_ok:
            logger.warning(
                "Token revocation failed or not supported — "
                "the token will expire on its own"
            )
    else:
        logger.info("No --token provided, skipping token revocation")

    # Summary
    print()
    if success:
        print(f"Twin {args.toe_id} has been deleted from the wallet controller.")
        if args.token:
            print("Access token revocation was attempted.")
    else:
        print(f"Failed to fully clean up twin {args.toe_id}. Check logs above.")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()