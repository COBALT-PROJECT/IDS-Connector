"""
SQLite storage for Authentication Manager JWTs.
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional


class AuthTokenStore:
    """Persist the latest OAuth token response in a local SQLite database."""

    def __init__(self, db_path: str = "authentication_tokens.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_tokens (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    access_token TEXT NOT NULL,
                    token_type TEXT,
                    scope TEXT,
                    expires_in INTEGER,
                    created_at TEXT NOT NULL,
                    expires_at TEXT
                )
                """
            )

    def save_token(self, token_data: Dict) -> Dict:
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("token_data must contain access_token")

        created_at = datetime.utcnow()
        expires_in = token_data.get("expires_in")
        expires_at = None
        if isinstance(expires_in, int):
            expires_at = (created_at + timedelta(seconds=expires_in)).isoformat() + "Z"

        record = {
            "access_token": access_token,
            "token_type": token_data.get("token_type", "Bearer"),
            "scope": token_data.get("scope"),
            "expires_in": expires_in,
            "created_at": created_at.isoformat() + "Z",
            "expires_at": expires_at,
        }

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO auth_tokens (
                    id, access_token, token_type, scope, expires_in, created_at, expires_at
                )
                VALUES (1, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    access_token = excluded.access_token,
                    token_type = excluded.token_type,
                    scope = excluded.scope,
                    expires_in = excluded.expires_in,
                    created_at = excluded.created_at,
                    expires_at = excluded.expires_at
                """,
                (
                    record["access_token"],
                    record["token_type"],
                    record["scope"],
                    record["expires_in"],
                    record["created_at"],
                    record["expires_at"],
                ),
            )

        return record

    def get_token(self) -> Optional[Dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT access_token, token_type, scope, expires_in, created_at, expires_at
                FROM auth_tokens
                WHERE id = 1
                """
            ).fetchone()

        return dict(row) if row else None

    def get_token_metadata(self) -> Optional[Dict]:
        token = self.get_token()
        if not token:
            return None

        return {
            "has_token": True,
            "token_type": token.get("token_type"),
            "scope": token.get("scope"),
            "expires_in": token.get("expires_in"),
            "created_at": token.get("created_at"),
            "expires_at": token.get("expires_at"),
        }
