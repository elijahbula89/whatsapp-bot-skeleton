# Adding a new client

1. **Make their folder.** Copy the right template into a new folder named after the business:
   `templates/cafe.yaml` → `clients/bula-bites-cafe/settings.yaml`
2. **Fill it in with the owner.** Menu or rooms with prices, hours, FAQs, how bookings work, payment methods. Anything left out, the bot will not answer; it hands those questions to staff.
3. **Get their language phrases checked.** Ask your iTaukei and Fiji Hindi testers for a greeting and a few common replies, and add them under `phrases:`.
4. **Test in your terminal** (no WhatsApp needed): `python -m app.chat bula-bites-cafe`. Send about 20 real questions in each language. Fix the settings file wherever an answer is wrong.
5. **Connect their WhatsApp number in Meta.** The business completes Meta business verification, then adds their number to the WhatsApp app in Meta. Copy the **Phone number ID** into `whatsapp_phone_number_id`.
6. **Set the staff alert number** in `staff_whatsapp`, starting with the country code and no + (for example `6799123456`).
7. **Restart the bot** so it loads the new folder. The log line `Loaded N client(s)` should include them.
8. **Send a test message from your own phone**, then hand over to the client.
