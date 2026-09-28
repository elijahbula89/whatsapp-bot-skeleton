"""Send a fixed set of test questions to the example bots and print the replies.

Needs ANTHROPIC_API_KEY. Usage:
    python -m scripts.live_test > live-test-results.md
Each question is a fresh chat, so replies don't lean on earlier answers.
"""

from app.brain import Brain
from app.clients import load_client
from app.config import load_config

QUESTIONS = {
    "example-cafe": [
        ("English", "What time do you open on Sunday?"),
        ("English", "Can I book a table for 4 people this Saturday at 7pm? My name is Mere."),
        ("English", "Can you help me write my school essay about climate change?"),
        ("iTaukei", "Bula! Na cava na kakana e rawa ni kana kina na kai vuli?"),
        ("iTaukei", "Au via vakarautaka e dua na teveli me ratou le 6 ena Vakarauwai."),
        ("Fiji Hindi", "Aap log ke paas vegetarian khana hai?"),
        ("Fiji Hindi", "Hum 3 log kal subah 9 baje aaye, table book kar do na."),
    ],
    "example-hostel": [
        ("English", "How much is a dorm bed per night?"),
        ("English", "I want to book a private room for 2 people from 12 to 15 October. Name is Tom."),
        ("English", "Who will win the rugby world cup?"),
        ("iTaukei", "E vica na isau ni moce ena dua na bogi?"),
        ("iTaukei", "Keirau via vakarautaka e dua na rumu me rua na bogi, mai na 20 ni Okotova."),
        ("Fiji Hindi", "Airport se aane ke liye pickup milega?"),
        ("Fiji Hindi", "Hum 2 log agle hafte 3 raat rukna chahte hai, room book kar do."),
    ],
}


def main() -> None:
    config = load_config()
    if not config.anthropic_api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY first (see .env.example).")
    brain = Brain(config.anthropic_api_key, config.model)
    for slug, questions in QUESTIONS.items():
        client = load_client(config.clients_dir / slug)
        print(f"## {client.business}\n")
        for language, question in questions:
            result = brain.reply(client, [], question)
            print(f"**{language}:** {question}\n\n> {result.text}\n")
            for note in result.staff_notes:
                print(f"Staff alert ({note.reason}): {note.summary}\n")


if __name__ == "__main__":
    main()
