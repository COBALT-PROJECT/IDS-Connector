#!/usr/bin/env python3
"""
Set the TOE ID on the IDS-TOE service.

Usage:
  python3 set_toe_id.py 3e671687-395b-41f5-a30f-a58921a69b79
  python3 set_toe_id.py 3e671687-395b-41f5-a30f-a58921a69b79 --base-url http://localhost:8005
"""
import argparse
import json
import sys
import uuid

import requests


DEFAULT_BASE_URL = "http://localhost:8005"


def parse_args():
    parser = argparse.ArgumentParser(description="Send a TOE ID to IDS-TOE.")
    parser.add_argument("toe_id", help="TOE UUID to store in IDS-TOE")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"IDS-TOE base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    toe_id = args.toe_id.strip()

    try:
        uuid.UUID(toe_id)
    except ValueError:
        print(f"Invalid TOE ID UUID: {toe_id}", file=sys.stderr)
        return 1

    base_url = args.base_url.rstrip("/")
    url = f"{base_url}/api/IDSconnector/TOE/id"
    payload = {"toe_id": toe_id}

    print(f"Sending TOE ID to {url}")

    try:
        response = requests.post(url, json=payload, timeout=args.timeout)
    except requests.exceptions.RequestException as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    print(f"Response status: {response.status_code}")

    try:
        print(json.dumps(response.json(), indent=2))
    except ValueError:
        print(response.text)

    return 0 if response.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
