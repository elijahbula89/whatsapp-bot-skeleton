"""The web server Meta sends WhatsApp messages to.

Run locally with:  uvicorn app.main:create_app --factory --reload
"""

import json
import logging

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request, Response

from app.brain import Brain
from app.clients import Client, load_all_clients
from app.config import load_config
from app.conversations import ConversationStore
from app.whatsapp import IncomingMessage, WhatsAppSender, parse_webhook, signature_is_valid

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot")

NOT_TEXT_REPLY = "Sorry, I can only read text messages for now. Please type your question. Vinaka!"


def create_app(config=None, brain=None, sender=None) -> FastAPI:
    config = config or load_config()
    clients = load_all_clients(config.clients_dir)
    brain = brain or Brain(config.anthropic_api_key, config.model)
    sender = sender or WhatsAppSender(config.access_token, config.graph_api_version)
    store = ConversationStore()
    log.info("Loaded %d client(s): %s", len(clients), ", ".join(c.slug for c in clients.values()))

    app = FastAPI(title="WhatsApp Bot Skeleton")

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, "clients": len(clients)}

    @app.get("/webhook")
    def verify(
        mode: str = Query("", alias="hub.mode"),
        token: str = Query("", alias="hub.verify_token"),
        challenge: str = Query("", alias="hub.challenge"),
    ) -> Response:
        """Meta calls this once when you connect the webhook, to check it's really yours."""
        if mode == "subscribe" and config.verify_token and token == config.verify_token:
            return Response(content=challenge, media_type="text/plain")
        raise HTTPException(status_code=403, detail="Verification failed")

    @app.post("/webhook")
    async def receive(request: Request, background: BackgroundTasks) -> dict:
        body = await request.body()
        if not signature_is_valid(config.app_secret, body, request.headers.get("X-Hub-Signature-256")):
            raise HTTPException(status_code=401, detail="Bad signature")
        try:
            payload = json.loads(body)
        except ValueError:
            raise HTTPException(status_code=400, detail="Not JSON")
        for msg in parse_webhook(payload):
            if store.already_handled(msg.message_id):
                continue
            client = clients.get(msg.phone_number_id)
            if client is None:
                log.warning("Message for unknown number %s; add it to a client's settings", msg.phone_number_id)
                continue
            # Answer Meta straight away and do the slow AI work afterwards,
            # otherwise Meta thinks the delivery failed and sends it again.
            background.add_task(handle_message, client, msg)
        return {"ok": True}

    def handle_message(client: Client, msg: IncomingMessage) -> None:
        sender.mark_read(client.phone_number_id, msg.message_id)
        if not msg.text:
            sender.send_text(client.phone_number_id, msg.customer, NOT_TEXT_REPLY)
            return
        history = store.get(client.slug, msg.customer)
        result = brain.reply(client, history, msg.text)
        sender.send_text(client.phone_number_id, msg.customer, result.text)
        store.add_exchange(client.slug, msg.customer, msg.text, result.text)
        for note in result.staff_notes:
            alert_staff(client, msg, note)

    def alert_staff(client: Client, msg: IncomingMessage, note) -> None:
        name = note.customer_name or msg.customer_name or "Customer"
        text = f"🔔 {note.reason.replace('_', ' ').title()}\n{name} (+{msg.customer})\n{note.summary}"
        log.info("Staff alert for %s: %s", client.slug, text.replace("\n", " | "))
        if client.staff_whatsapp:
            if not sender.send_text(client.phone_number_id, client.staff_whatsapp, text):
                log.warning("Staff alert for %s not delivered by WhatsApp; see log line above", client.slug)

    return app

