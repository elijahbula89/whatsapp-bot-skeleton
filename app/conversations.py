"""Remembers recent messages with each customer so the bot can follow the conversation.

This keeps history in memory, so it is forgotten when the server restarts.
That is fine for a pilot; swap in a database later if needed.
"""

import time
from collections import OrderedDict
from threading import Lock

MAX_TURNS = 20  # messages kept per customer
FORGET_AFTER_SECONDS = 24 * 60 * 60  # matches WhatsApp's 24-hour reply window
MAX_CUSTOMERS = 5000
MAX_SEEN_IDS = 10000


class ConversationStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._history: OrderedDict[tuple[str, str], tuple[float, list[dict]]] = OrderedDict()
        self._seen_ids: OrderedDict[str, None] = OrderedDict()

    def already_handled(self, message_id: str) -> bool:
        """Meta sometimes delivers the same message twice. Returns True the second time."""
        with self._lock:
            if message_id in self._seen_ids:
                return True
            self._seen_ids[message_id] = None
            if len(self._seen_ids) > MAX_SEEN_IDS:
                self._seen_ids.popitem(last=False)
            return False

    def get(self, client_slug: str, customer: str) -> list[dict]:
        with self._lock:
            entry = self._history.get((client_slug, customer))
            if not entry or time.time() - entry[0] > FORGET_AFTER_SECONDS:
                return []
            return list(entry[1])

    def add_exchange(self, client_slug: str, customer: str, user_text: str, reply: str) -> None:
        key = (client_slug, customer)
        with self._lock:
            entry = self._history.get(key)
            turns = list(entry[1]) if entry and time.time() - entry[0] <= FORGET_AFTER_SECONDS else []
            turns += [{"role": "user", "content": user_text}, {"role": "assistant", "content": reply}]
            self._history[key] = (time.time(), turns[-MAX_TURNS:])
            self._history.move_to_end(key)
            if len(self._history) > MAX_CUSTOMERS:
                self._history.popitem(last=False)
