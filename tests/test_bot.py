import hashlib
import hmac
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.brain import FALLBACK_REPLY, Brain, BotReply, StaffNote
from app.clients import ClientConfigError, load_all_clients, load_client
from app.config import load_config
from app.conversations import ConversationStore
from app.main import create_app
from app.prompt import build_system_prompt
from app.whatsapp import parse_webhook, signature_is_valid

ROOT = Path(__file__).resolve().parent.parent
CLIENTS = ROOT / "clients"
SECRET = "test-secret"


def webhook_payload(text="Bula, are you open Sunday?", phone_number_id="1314632248404429", msg_id="wamid.1"):
    return {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {
            "metadata": {"phone_number_id": phone_number_id},
            "contacts": [{"wa_id": "6799990000", "profile": {"name": "Mere"}}],
            "messages": [{"id": msg_id, "from": "6799990000", "type": "text", "text": {"body": text}}],
        }}]}],
    }


def signed(body: bytes) -> dict:
    return {"X-Hub-Signature-256": "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()}


# --- client settings files ---

def test_example_clients_load():
    clients = load_all_clients(CLIENTS)
    assert {c.slug for c in clients.values()} == {"example-cafe", "example-hostel"}


@pytest.mark.parametrize("name", ["cafe", "hostel", "real_estate"])
def test_templates_are_valid(tmp_path, name):
    folder = tmp_path / name
    folder.mkdir()
    (folder / "settings.yaml").write_text((ROOT / "templates" / f"{name}.yaml").read_text())
    assert load_client(folder).business


def test_missing_required_field_is_explained(tmp_path):
    (tmp_path / "settings.yaml").write_text("business: X\n")
    with pytest.raises(ClientConfigError, match="industry"):
        load_client(tmp_path)


def test_duplicate_number_rejected(tmp_path):
    for name in ("a", "b"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "settings.yaml").write_text("business: X\nindustry: cafe\nwhatsapp_phone_number_id: '1'\n")
    with pytest.raises(ClientConfigError, match="same"):
        load_all_clients(tmp_path)


def test_prompt_has_business_facts_but_not_program_settings():
    client = load_client(CLIENTS / "example-cafe")
    prompt = build_system_prompt(client)
    assert "Lovo chicken plate" in prompt and "iTaukei" in prompt
    assert "1314632248404429" not in prompt


# --- WhatsApp messages ---

def test_parse_text_message():
    [msg] = parse_webhook(webhook_payload())
    assert (msg.customer, msg.customer_name, msg.text) == ("6799990000", "Mere", "Bula, are you open Sunday?")


def test_parse_ignores_status_updates():
    payload = {"entry": [{"changes": [{"value": {"metadata": {"phone_number_id": "1"}, "statuses": [{"id": "x"}]}}]}]}
    assert parse_webhook(payload) == []


def test_voice_note_has_no_text():
    payload = webhook_payload()
    payload["entry"][0]["changes"][0]["value"]["messages"][0] = {"id": "w2", "from": "679", "type": "audio"}
    [msg] = parse_webhook(payload)
    assert msg.text is None


def test_signature_check():
    body = b'{"a":1}'
    assert signature_is_valid(SECRET, body, signed(body)["X-Hub-Signature-256"])
    assert not signature_is_valid(SECRET, body, "sha256=wrong")
    assert not signature_is_valid("", body, signed(body)["X-Hub-Signature-256"])


# --- conversation memory ---

def test_store_dedupes_and_keeps_history():
    store = ConversationStore()
    assert not store.already_handled("m1")
    assert store.already_handled("m1")
    store.add_exchange("cafe", "679", "hi", "Bula!")
    assert store.get("cafe", "679") == [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "Bula!"}]
    assert store.get("cafe", "other") == []


# --- Claude brain (with a fake Claude, so no API key needed) ---

class FakeClaude:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def text_response(text):
    return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)])


def tool_response():
    block = SimpleNamespace(type="tool_use", id="t1", name="notify_staff",
                            input={"reason": "booking", "summary": "Table for 4 Friday 12pm", "customer_name": "Mere"})
    return SimpleNamespace(stop_reason="tool_use", content=[block])


def make_brain(fake):
    return Brain("key", "claude-sonnet-5", client_factory=lambda **_: fake)


def test_brain_plain_reply():
    fake = FakeClaude([text_response("Bula! Sorry, we're closed on Sundays.")])
    result = make_brain(fake).reply(load_client(CLIENTS / "example-cafe"), [], "Open Sunday?")
    assert result.text == "Bula! Sorry, we're closed on Sundays."
    assert fake.calls[0]["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_brain_staff_handover():
    fake = FakeClaude([tool_response(), text_response("Vinaka Mere, staff will confirm your table soon.")])
    result = make_brain(fake).reply(load_client(CLIENTS / "example-cafe"), [], "Table for 4 Friday noon")
    assert result.staff_notes == [StaffNote("booking", "Table for 4 Friday 12pm", "Mere")]
    assert fake.calls[1]["messages"][-1]["content"][0]["type"] == "tool_result"


def test_brain_keeps_reply_written_before_staff_handover():
    first = tool_response()
    first.content.insert(0, SimpleNamespace(type="text", text="Sorry Mere, we close at 4pm. Staff will message you."))
    fake = FakeClaude([first])
    result = make_brain(fake).reply(load_client(CLIENTS / "example-cafe"), [], "Table for 4 Saturday 7pm")
    assert result.text == "Sorry Mere, we close at 4pm. Staff will message you."
    assert result.staff_notes == [StaffNote("booking", "Table for 4 Friday 12pm", "Mere")]
    assert len(fake.calls) == 1


def test_brain_falls_back_on_empty_reply():
    fake = FakeClaude([text_response("  ")])
    assert make_brain(fake).reply(load_client(CLIENTS / "example-cafe"), [], "hi").text == FALLBACK_REPLY


# --- the web server end to end ---

class FakeBrain:
    def reply(self, client, history, text):
        return BotReply(f"reply to: {text}", [StaffNote("booking", "wants a table")])


class FakeSender:
    def __init__(self):
        self.sent = []

    def send_text(self, phone_number_id, to, text):
        self.sent.append((phone_number_id, to, text))
        return True

    def mark_read(self, phone_number_id, message_id):
        pass


@pytest.fixture
def server():
    config = replace(load_config(), verify_token="word", app_secret=SECRET, clients_dir=CLIENTS)
    sender = FakeSender()
    return TestClient(create_app(config=config, brain=FakeBrain(), sender=sender)), sender


def test_webhook_verification(server):
    http, _ = server
    ok = http.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "word", "hub.challenge": "123"})
    assert ok.status_code == 200 and ok.text == "123"
    assert http.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "no", "hub.challenge": "1"}).status_code == 403


def test_message_gets_reply_once(server):
    http, sender = server
    body = json.dumps(webhook_payload("Hi")).encode()
    assert http.post("/webhook", content=body, headers=signed(body)).status_code == 200
    assert http.post("/webhook", content=body, headers=signed(body)).status_code == 200  # Meta retry
    assert sender.sent == [("1314632248404429", "6799990000", "reply to: Hi")]  # no staff number set


def test_unsigned_message_rejected(server):
    http, sender = server
    body = json.dumps(webhook_payload()).encode()
    assert http.post("/webhook", content=body).status_code == 401
    assert sender.sent == []
