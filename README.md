# WhatsApp Bot Skeleton

One AI WhatsApp bot that you can reuse for many small businesses in Fiji. It answers customers in **English, iTaukei and Fiji Hindi** and passes bookings, orders and complaints to staff.

## How it works

```
Customer on WhatsApp → Meta → this bot → Claude (AI) → reply sent back on WhatsApp
```

- **One program** (the `app/` folder) runs every client.
- **Each client is a folder** in `clients/` containing one `settings.yaml` file. That file holds their menu or rooms, prices, hours, FAQs and tone. The bot only uses facts from this file and never makes up prices.
- **Templates** in `templates/` get you started for cafés, hostels/backpackers and real estate agents.
- When a customer wants to book or order, asks for a person, or asks something the file doesn't cover, the bot tells them staff will follow up. It then sends the staff number an alert on WhatsApp.

## What's in here

| Path | What it is |
|---|---|
| `app/main.py` | The web server Meta sends messages to |
| `app/brain.py` | Asks Claude for the reply and handles staff alerts |
| `app/prompt.py` | The rules the bot follows (stay on topic, answer in the customer's language) |
| `app/whatsapp.py` | Reads incoming WhatsApp messages and sends replies |
| `app/chat.py` | Lets you chat with a client's bot in your terminal, without WhatsApp |
| `clients/` | One folder per business. The two examples are made up. |
| `templates/` | Starting points for new clients |
| `docs/new-client-checklist.md` | Step-by-step guide to adding a client |

## Setting it up on your computer

You need Python 3.11 or newer.

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in the keys (see the notes inside)
python -m pytest            # checks everything works; no keys needed
```

Once you have a Claude API key, you can chat with the example café:

```bash
export $(cat .env | xargs)
python -m app.chat example-cafe
```

## Connecting to WhatsApp

1. In [Meta for Developers](https://developers.facebook.com), create an app of type **Business** and add the **WhatsApp** product. Meta gives you a free test number.
2. Put the bot online so Meta can reach it: `uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000`. For quick tests from your computer, use a tunnel tool such as ngrok.
3. In Meta, go to **WhatsApp → Configuration → Webhook**. Enter `https://your-address/webhook` and your `WHATSAPP_VERIFY_TOKEN`, then subscribe to **messages**.
4. Copy the test number's **Phone number ID** into a client's `settings.yaml`, restart, and message the test number from your phone.

## Good to know

- **Replies are free on Meta's side** when they're sent within 24 hours of the customer's last message. That covers almost everything this bot does.
- **Staff alerts are also WhatsApp messages**, so Meta only delivers them if the staff number has messaged the business number in the last 24 hours. A missed alert is still written to the server log. For the pilot, we'll set up an approved Meta "utility" message template so alerts always get through.
- **Conversation memory** lasts 24 hours and is cleared when the server restarts. That's fine for a pilot.
- **Meta's AI rules (2026):** general "ask me anything" bots are banned on WhatsApp. This bot only talks about the one business it belongs to, which is allowed.
