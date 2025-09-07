# api/session_store.py
from typing import Dict, Any, Optional
import threading

class SessionStore:
    """
    Tiny in-memory session store. Thread-safe for simple background tasks.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._store: Dict[str, Dict[str, Any]] = {}

    def create_session(self, session_id: str, meta: Dict[str, Any]) -> None:
        with self._lock:
            self._store[session_id] = {"meta": meta, "transcript": None}

    def set_transcript(self, session_id: str, transcript: list) -> None:
        with self._lock:
            if session_id in self._store:
                self._store[session_id]["transcript"] = transcript

    def get_transcript(self, session_id: str) -> Optional[list]:
        with self._lock:
            return self._store.get(session_id, {}).get("transcript")

    def exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._store
