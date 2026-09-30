# CLAUDE.md

Guidance for Claude Code working in this repo. Read it before doing anything.

## Who you're working with

- The owner is Elijah, in Fiji. He is new to code and servers: explain simply, step by step, and explain any jargon you use.
- Be direct and skip the fluff. Lead with the answer.
- **Ask before anything big**: new features, new dependencies, new services, anything that costs money, or changes to hosting. Small fixes are fine.
- When he has to click through Meta or Render, give exact numbered steps and say what he should see if it worked.
- Never ask him to paste secrets (API keys, tokens, passwords) into the chat, and never write them into the repo. They live in `.env` locally and in Render → Environment in production.

## What this project is

AI WhatsApp chatbots for small and medium businesses in Fiji (cafes and restaurants, hostels and backpackers, tourism, real estate). One reusable bot runs every client; each client is just a settings file. The bot answers only from that business's facts and hands bookings, orders, complaints and unknown questions to staff.

```
Customer on WhatsApp → Meta WhatsApp Cloud API → this app (on Render) → Claude API → reply on WhatsApp
```

## Layout

| Path | What it is |
|---|---|
| `app/main.py` | FastAPI app (`create_app` factory); `/webhook` for Meta, `/health` for Render |
| `app/brain.py` | Asks Claude for the reply, sends staff alerts |
| `app/prompt.py` | The bot's rules (stay on topic, English only, never invent facts) |
| `app/whatsapp.py` | Parses incoming Meta webhooks, sends replies |
| `app/clients.py` | Loads every `clients/*/settings.yaml` |
| `app/config.py` | Reads environment variables |
| `app/conversations.py` | 24-hour in-memory chat history (cleared on restart) |
| `app/chat.py` | Chat with a client's bot in the terminal, no WhatsApp needed |
| `clients/<slug>/settings.yaml` | One folder per business. `example-cafe` and `example-hostel` are made up |
| `templates/` | Starting files: `cafe.yaml`, `hostel.yaml`, `real_estate.yaml` |
| `docs/new-client-checklist.md` | Steps to add a client |
| `render.yaml` | Render blueprint (free plan, Python 3.11) |
| `scripts/live_test.py` | Live test against the real Claude API |
| `tests/test_bot.py` | Tests with fakes; no keys needed |

## Commands

```bash
pip install -r requirements.txt
python -m pytest -q                      # run before every commit; CI runs the same
python -m app.chat example-cafe          # needs a Claude key in the environment
uvicorn app.main:create_app --factory --port 8000
```

## Rules for changes

- Keep one codebase for all clients. Client differences go in `settings.yaml`, not in code.
- The bot must only use facts in the client's settings file. Never let it invent prices, dishes, rooms or availability, and never confirm a booking or order (staff confirm).
- Keep each bot scoped to its own business: Meta's 2026 rules ban general "ask me anything" AI bots on WhatsApp.
- Replies are English only for now. iTaukei and Fiji Hindi are parked; any new language needs about 20 test questions checked by a native speaker (Elijah has testers).
- Add or update a test in `tests/` for any behaviour change.
- Work on a branch and open a pull request; Render redeploys when `main` changes.

## Environment variables

`BOT_ANTHROPIC_API_KEY` (or `ANTHROPIC_API_KEY`), `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN`. Optional: `CLAUDE_MODEL` (default `claude-sonnet-5`), `WHATSAPP_GRAPH_VERSION`. See `.env.example`.

## Current status (30 September 2026)

- Live on WhatsApp with Meta's test number, hosted on Render's free plan. The example cafe replies to Elijah's texts.
- No real client yet. First pilot will be a cafe or a small hostel/backpackers.

## Known gotchas

1. **Meta's temporary access token expires after about 24 hours.** The bot then stops replying silently and Render logs show "WhatsApp refused message". Fix: a permanent System User token (not done yet).
2. **Webhook "Test" works but real messages never arrive** until the WhatsApp Business Account is subscribed to the app: Graph API Explorer → `POST <WABA ID>/subscribed_apps`. Needed for every new client.
3. **Render's free plan sleeps** after about 15 minutes idle, so the first reply takes about a minute. Real clients need a paid plan.
4. **Staff alerts only arrive** if the staff number messaged the business number in the last 24 hours. Fix: an approved Meta "utility" message template (not done yet).
5. **The key is read from `BOT_ANTHROPIC_API_KEY`** as well as `ANTHROPIC_API_KEY`, because Claude's cloud environment reserves the normal name. Keep both working.
6. To debug production, ask Elijah for Render log screenshots (search "webhook", "ERROR", "WARNING").

## Next steps

1. One-time setup before any real client: permanent System User token, Render paid plan, approved staff-alert template.
2. Pick and onboard the first pilot with `docs/new-client-checklist.md`, then remove the made-up example clients.
3. Later: pricing for clients, then iTaukei and Fiji Hindi.
