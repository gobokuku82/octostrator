"""Development checkpointer using SQLite"""

import os
import json
import pickle
import sqlite3
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint
from langgraph.checkpoint.serde import SerializerProtocol
from loguru import logger


class SQLiteCheckpointer(BaseCheckpointSaver):
    """Simple SQLite checkpointer for development"""

    def __init__(self, db_path: str = "checkpoints.db"):
        """Initialize SQLite checkpointer"""
        self.db_path = db_path
        self.serde = self.serde  # Use default serializer
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create checkpoints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT NOT NULL,
                checkpoint_id TEXT NOT NULL,
                parent_checkpoint_id TEXT,
                checkpoint_data BLOB,
                metadata TEXT,
                created_at TEXT,
                PRIMARY KEY (thread_id, checkpoint_id)
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"SQLite checkpointer initialized at {self.db_path}")

    def put(self, config: Dict, checkpoint: Checkpoint, metadata: Dict) -> Dict:
        """Save checkpoint"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint_id = checkpoint.get("id", str(datetime.now().timestamp()))
        parent_id = checkpoint.get("parent_id")

        # Serialize checkpoint
        checkpoint_data = pickle.dumps(checkpoint)
        metadata_json = json.dumps(metadata)

        # Insert or replace checkpoint
        cursor.execute("""
            INSERT OR REPLACE INTO checkpoints
            (thread_id, checkpoint_id, parent_checkpoint_id, checkpoint_data, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (thread_id, checkpoint_id, parent_id, checkpoint_data, metadata_json, datetime.now().isoformat()))

        conn.commit()
        conn.close()

        logger.debug(f"Saved checkpoint {checkpoint_id} for thread {thread_id}")
        return {"configurable": {"thread_id": thread_id, "checkpoint_id": checkpoint_id}}

    def get(self, config: Dict) -> Optional[Checkpoint]:
        """Get checkpoint"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")

        if checkpoint_id:
            # Get specific checkpoint
            cursor.execute("""
                SELECT checkpoint_data FROM checkpoints
                WHERE thread_id = ? AND checkpoint_id = ?
            """, (thread_id, checkpoint_id))
        else:
            # Get latest checkpoint
            cursor.execute("""
                SELECT checkpoint_data FROM checkpoints
                WHERE thread_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (thread_id,))

        result = cursor.fetchone()
        conn.close()

        if result:
            checkpoint = pickle.loads(result[0])
            logger.debug(f"Retrieved checkpoint for thread {thread_id}")
            return checkpoint

        return None

    def get_tuple(self, config: Dict) -> Optional[tuple]:
        """Get checkpoint as tuple"""
        checkpoint = self.get(config)
        if checkpoint:
            return (checkpoint, config)
        return None

    async def aget(self, config: Dict) -> Optional[Checkpoint]:
        """Async get (just wraps sync version for development)"""
        return self.get(config)

    async def aput(self, config: Dict, checkpoint: Checkpoint, metadata: Dict) -> Dict:
        """Async put (just wraps sync version for development)"""
        return self.put(config, checkpoint, metadata)

    async def aget_tuple(self, config: Dict) -> Optional[tuple]:
        """Async get tuple"""
        return self.get_tuple(config)


class InMemoryStore:
    """Simple in-memory store for development"""

    def __init__(self):
        """Initialize in-memory store"""
        self.data: Dict[str, Dict[str, Any]] = {}
        logger.info("In-memory store initialized")

    async def put(self, namespace: tuple, key: str, value: Any):
        """Store value"""
        ns_key = str(namespace)
        if ns_key not in self.data:
            self.data[ns_key] = {}
        self.data[ns_key][key] = value
        logger.debug(f"Stored {key} in namespace {namespace}")

    async def get(self, namespace: tuple, key: str) -> Any:
        """Get value"""
        ns_key = str(namespace)
        value = self.data.get(ns_key, {}).get(key)
        logger.debug(f"Retrieved {key} from namespace {namespace}")
        return value

    async def search(self, namespace: tuple, query: str, limit: int = 5) -> list:
        """Simple search (just returns all items for development)"""
        ns_key = str(namespace)
        items = list(self.data.get(ns_key, {}).values())[:limit]
        logger.debug(f"Searched namespace {namespace}, found {len(items)} items")
        return items

    async def delete(self, namespace: tuple, key: str):
        """Delete value"""
        ns_key = str(namespace)
        if ns_key in self.data and key in self.data[ns_key]:
            del self.data[ns_key][key]
            logger.debug(f"Deleted {key} from namespace {namespace}")