"""Persistent State Manager using MongoDB Atlas.

Each client has its own namespace.
State tetap bisa dipanggil secara synchronous:
    state.set(...)
    state.get(...)
    state.delete(...)

Data tersimpan di MongoDB sehingga tidak hilang ketika bot restart.
"""

from typing import Any

from pymongo import MongoClient

from config import MONGO_DB_URI, DB_NAME


class State:
    """State manager with MongoDB persistence."""

    def __init__(self):
        if not MONGO_DB_URI:
            raise ValueError(
                "MONGO_DB_URI belum diset di config.py / .env"
            )

        self.mongo = MongoClient(
            MONGO_DB_URI,
            serverSelectionTimeoutMS=10000,
        )

        self.db = self.mongo[DB_NAME]
        self.collection = self.db.states

        # Satu document untuk setiap client.
        self.collection.create_index(
            "client_id",
            unique=True,
        )

        # Test koneksi
        self.mongo.admin.command("ping")

        print("✅ State MongoDB connected")

    def set(
        self,
        client_id: str,
        key: str,
        value: Any,
    ) -> None:
        """Set a value for a specific client."""

        self.collection.update_one(
            {
                "client_id": str(client_id),
            },
            {
                "$set": {
                    f"data.{key}": value,
                }
            },
            upsert=True,
        )

    def get(
        self,
        client_id: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """Get a value for a specific client."""

        document = self.collection.find_one(
            {
                "client_id": str(client_id),
            },
            {
                f"data.{key}": 1,
                "_id": 0,
            },
        )

        if not document:
            return default

        return document.get(
            "data",
            {},
        ).get(
            key,
            default,
        )

    def delete(
        self,
        client_id: str,
        key: str,
    ) -> bool:
        """Delete a specific state key."""

        document = self.collection.find_one(
            {
                "client_id": str(client_id),
                f"data.{key}": {
                    "$exists": True,
                },
            }
        )

        if not document:
            return False

        result = self.collection.update_one(
            {
                "client_id": str(client_id),
            },
            {
                "$unset": {
                    f"data.{key}": "",
                }
            },
        )

        return result.modified_count > 0

    def clear_client(
        self,
        client_id: str,
    ) -> None:
        """Clear all state for one client."""

        self.collection.delete_one(
            {
                "client_id": str(client_id),
            }
        )

    def clear_all(self) -> None:
        """Clear all states."""

        self.collection.delete_many({})

    def get_client_keys(
        self,
        client_id: str,
    ) -> list:
        """Get all keys belonging to a client."""

        document = self.collection.find_one(
            {
                "client_id": str(client_id),
            },
            {
                "data": 1,
                "_id": 0,
            },
        )

        if not document:
            return []

        return list(
            document.get(
                "data",
                {}
            ).keys()
        )

    def has_key(
        self,
        client_id: str,
        key: str,
    ) -> bool:
        """Check whether a state key exists."""

        document = self.collection.find_one(
            {
                "client_id": str(client_id),
                f"data.{key}": {
                    "$exists": True,
                },
            },
            {
                "_id": 1,
            },
        )

        return document is not None

    def close(self):
        """Close MongoDB connection."""

        if self.mongo:
            self.mongo.close()


# Global state instance
state = State()
