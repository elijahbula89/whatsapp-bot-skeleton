"""Chat with a client's bot in your terminal, without WhatsApp.

Needs ANTHROPIC_API_KEY. Usage:
    python -m app.chat example-cafe
Type 'quit' to stop.
"""

import sys

from app.brain import Brain
from app.clients import load_client
from app.config import load_config


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m app.chat <client-folder-name>")
        sys.exit(1)
    config = load_config()
    if not config.anthropic_api_key:
        print("Set ANTHROPIC_API_KEY first (see .env.example).")
        sys.exit(1)
    client = load_client(config.clients_dir / sys.argv[1])
    brain = Brain(config.anthropic_api_key, config.model)
    history: list[dict] = []
    print(f"Chatting with {client.business}. Type 'quit' to stop.\n")
    while True:
        try:
            text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in {"quit", "exit"}:
            break
        if not text:
            continue
        result = brain.reply(client, history, text)
        print(f"\nBot: {result.text}\n")
        for note in result.staff_notes:
            print(f"   [staff alert: {note.reason}] {note.summary}\n")
        history += [{"role": "user", "content": text}, {"role": "assistant", "content": result.text}]


if __name__ == "__main__":
    main()
