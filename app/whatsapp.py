"""Talking to Meta's WhatsApp Cloud API: reading incoming messages and sending replies."""

import hashlib
import hmac
import logging
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)


@dataclass
class IncomingMessage:
    message_id: str
    phone_number_id: str  # which business number it was sent to
    customer: str  # customer's WhatsApp number
    customer_name: str | None
    text: str | None  # None for photos, voice notes, stickers etc.


def signature_is_valid(app_secret: str, body: bytes, header: str | None) -> bool:
    """Checks the X-Hub-Signature-256 header so strangers can't fake messages."""
    if not app_secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def parse_webhook(payload: dict) -> list[IncomingMessage]:
    """Pulls customer messages out of Meta's webhook JSON. Ignores delivery receipts."""
    found = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id")
            names = {c.get("wa_id"): c.get("profile", {}).get("name") for c in value.get("contacts", [])}
            for msg in value.get("messages", []):
                if not phone_number_id or "from" not in msg or "id" not in msg:
                    continue
                if msg.get("type") == "text":
                    text = msg.get("text", {}).get("body")
                elif msg.get("type") == "button":
                    text = msg.get("button", {}).get("text")
                elif msg.get("type") == "interactive":
                    inter = msg.get("interactive", {})
                    text = (inter.get("button_reply") or inter.get("list_reply") or {}).get("title")
                else:
                    text = None
                found.append(IncomingMessage(msg["id"], phone_number_id, msg["from"], names.get(msg["from"]), text))
    return found


class WhatsAppSender:
    def __init__(self, access_token: str, graph_api_version: str, http: httpx.Client | None = None) -> None:
        self._token = access_token
        self._base = f"https://graph.facebook.com/{graph_api_version}"
        self._http = http or httpx.Client(timeout=15.0)

    def send_text(self, phone_number_id: str, to: str, text: str) -> bool:
        """Returns False if Meta refused (for example, outside the 24-hour reply window)."""
        try:
            r = self._http.post(
                f"{self._base}/{phone_number_id}/messages",
                headers={"Authorization": f"Bearer {self._token}"},
                json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text[:4096]}},
            )
        except httpx.HTTPError:
            log.exception("Could not reach WhatsApp")
            return False
        if r.status_code >= 400:
            log.error("WhatsApp refused message to %s: %s %s", to, r.status_code, r.text[:500])
            return False
        return True

    def mark_read(self, phone_number_id: str, message_id: str) -> None:
        """Shows the customer blue ticks so they know the message arrived."""
        try:
            self._http.post(
                f"{self._base}/{phone_number_id}/messages",
                headers={"Authorization": f"Bearer {self._token}"},
                json={"messaging_product": "whatsapp", "status": "read", "message_id": message_id},
            )
        except httpx.HTTPError:
            log.warning("Could not mark message as read")
