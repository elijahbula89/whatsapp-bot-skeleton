# Adding a new client

Full guide with the Meta clicks: https://claude.ai/artifact/E87p9KFD2s6UYwTZ6xwNky

**Once only, before the first real client:** a permanent System User access token in Render (`WHATSAPP_ACCESS_TOKEN`), Render on a paid plan so the bot never sleeps, and an approved staff-alert message template.

1. **First meeting.** Copy the right template into a new folder named after the business
   (`templates/cafe.yaml` → `clients/bula-bites-cafe/settings.yaml`) and fill it in with the owner:
   menu or rooms with prices, hours, FAQs, how bookings work, payment methods, staff alert number.
   Anything left out, the bot will not answer; it hands those questions to staff.
2. **Phone number.** Use a number that is not on the normal WhatsApp app (a new SIM is easiest).
3. **Client's Meta account.** The business creates a Meta business portfolio, starts business
   verification, adds the number in WhatsApp Manager, and shares the WhatsApp account with you as a partner.
4. **Connect it.** Give your System User access to their WhatsApp account, then in Graph API Explorer
   send `POST <their WhatsApp Business Account ID>/subscribed_apps`. Put their **Phone number ID**
   into `whatsapp_phone_number_id` and the staff number (country code first, no +) into `staff_whatsapp`.
5. **Test** in your terminal (no WhatsApp needed): `python -m app.chat bula-bites-cafe`.
   Send about 20 real questions and fix the settings file wherever an answer is wrong.
6. **Go live.** Merge the change; Render restarts and the log line `Loaded N client(s)` should include them.
   Message the number from your own phone, test a booking alert, then hand over to the owner.
