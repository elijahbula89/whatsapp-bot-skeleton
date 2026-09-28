"""Asks Claude to write the reply, and lets it flag conversations for staff."""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

import anthropic

from app.clients import Client
from app.prompt import build_system_prompt

log = logging.getLogger(__name__)

NOTIFY_STAFF_TOOL = {
    "name": "notify_staff",
    "description": (
        "Send a note to the business's staff so a human follows up with this customer. "
        "Use for bookings, orders, viewing requests, complaints, requests for a human, "
        "and questions the business information does not answer."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "enum": ["booking", "order", "viewing", "lead", "complaint", "human_requested", "unanswered_question"],
            },
            "summary": {
                "type": "string",
                "description": "One or two sentences in English for staff: what the customer wants, with any details given (dates, numbers of people, budget).",
            },
            "customer_name": {"type": "string", "description": "The customer's name if they gave it."},
        },
        "required": ["reason", "summary"],
        "additionalProperties": False,
    },
    "strict": True,
}

FALLBACK_REPLY = "Sorry, I'm having trouble right now. A staff member will reply to you soon. Vinaka!"
MAX_TOOL_ROUNDS = 3


@dataclass
class StaffNote:
    reason: str
    summary: str
    customer_name: str | None = None


@dataclass
class BotReply:
    text: str
    staff_notes: list[StaffNote] = field(default_factory=list)


class Brain:
    def __init__(self, api_key: str, model: str, client_factory: Callable[..., Any] | None = None) -> None:
        factory = client_factory or anthropic.Anthropic
        self._claude = factory(api_key=api_key, timeout=30.0, max_retries=2)
        self._model = model

    def reply(self, client: Client, history: list[dict], customer_text: str) -> BotReply:
        system = [{"type": "text", "text": build_system_prompt(client), "cache_control": {"type": "ephemeral"}}]
        messages: list[dict] = [*history, {"role": "user", "content": customer_text}]
        notes: list[StaffNote] = []

        for _ in range(MAX_TOOL_ROUNDS):
            try:
                response = self._claude.messages.create(
                    model=self._model,
                    max_tokens=1024,
                    system=system,
                    tools=[NOTIFY_STAFF_TOOL],
                    output_config={"effort": "low"},  # quick, cheap replies suit short chats
                    messages=messages,
                )
            except anthropic.APIError:
                log.exception("Claude request failed for %s", client.slug)
                return BotReply(FALLBACK_REPLY, notes)

            text = "".join(b.text for b in response.content if b.type == "text").strip()
            if response.stop_reason != "tool_use":
                return BotReply(text or FALLBACK_REPLY, notes)

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                if block.name == "notify_staff":
                    args = dict(block.input)
                    notes.append(StaffNote(args.get("reason", "lead"), args.get("summary", ""), args.get("customer_name")))
                    result = {"type": "tool_result", "tool_use_id": block.id, "content": "Staff have been notified."}
                else:
                    result = {"type": "tool_result", "tool_use_id": block.id, "content": "Unknown tool.", "is_error": True}
                tool_results.append(result)
            if text:
                # Claude already wrote the customer's reply before calling the tool; send that
                # rather than asking again, which would drop it or add a second message.
                return BotReply(text, notes)
            messages += [{"role": "assistant", "content": response.content}, {"role": "user", "content": tool_results}]

        log.warning("Too many tool rounds for %s", client.slug)
        return BotReply(FALLBACK_REPLY, notes)
