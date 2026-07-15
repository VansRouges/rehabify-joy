# WhatsApp Cloud API Integration Guide (Joy)

**Status:** Fact-checked against the Rehabify Joy codebase and Meta WhatsApp Cloud API docs (as of July 2026).

**Purpose:** Connect Joy on WhatsApp using Meta's **WhatsApp Business Cloud API**, with `+234 812 261 5453` as the business number. The existing FastAPI backend is the right integration point — WhatsApp becomes another channel into the same Joy logic used by the web app.

---

## Corrections applied to the original draft


| Topic                 | Original draft                                    | Corrected                                                                                                                                                                                     |
| --------------------- | ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Graph API version     | `v21.0`                                           | Use a current version (e.g. `v25.0`) and pin it in config; Meta updates versions regularly                                                                                                    |
| `to` field format     | Digits only, no `+`                               | Meta's 2026 docs show `to` **with** `+` (e.g. `"+2348122615453"`). Digits-only often works, but follow official examples and test both                                                        |
| Webhook response time | "within 5 seconds"                                | Return **HTTP 200 immediately** (target **< 3 seconds**). Do all Gemini/DB work **asynchronously**                                                                                            |
| Webhook security      | Not mentioned                                     | **Required:** validate `X-Hub-Signature-256` with your **App Secret** on every POST                                                                                                           |
| Phone coexistence     | Must delete personal WhatsApp                     | Oversimplified. **Personal WhatsApp** cannot coexist with API. **WhatsApp Business App + Cloud API coexistence** is a separate official path (see below)                                      |
| Pricing model         | "Conversation categories & pricing" (CBP framing) | Since **July 1, 2025**: **per-message** pricing for **template** messages; **non-template** replies inside the customer service window are **free**                                           |
| Env vars              | 4 WhatsApp vars                                   | Add `WHATSAPP_APP_SECRET` (signature verification) and `WHATSAPP_GRAPH_API_VERSION`                                                                                                           |
| Webhook path          | `/webhook`                                        | Must match your FastAPI mount exactly. This repo's API routes live under `/api/*`; either use `/webhook` at app root or `/api/webhook` and register that full URL in Meta                     |
| WABA ID               | Listed as required for sending                    | **Phone Number ID + access token** are required to send. **WABA ID** is needed for subscription troubleshooting and some admin APIs, not basic send                                           |
| Voice on WhatsApp     | "Download media URL from Meta"                    | Two-step flow: webhook gives a **media ID** → `GET /{media-id}` → download from returned URL with Bearer token                                                                                |
| Codebase gaps         | Implied ready to wire                             | No WhatsApp code exists yet. Reuse `process_message()`, `normalize_phone()`, `transcribe_audio()` — but add channel adapter, signature verification, async queue, and patient-by-phone lookup |


---



## Big picture

```
User on WhatsApp (+2348122615453)
        ↓
Meta Cloud API (webhook POST)
        ↓
FastAPI on Railway  ← same Gemini, Redis, Postgres, safety rules
        ↓
Meta Cloud API (POST /{PHONE_NUMBER_ID}/messages)
        ↓
User sees Joy on WhatsApp
```

Web and WhatsApp share one brain. Only the **inbound/outbound adapter** changes.

**What already exists in this repo:**

- Chat orchestration: `backend/app/services/chat_service.py` → `process_message()`
- Phone normalization: `backend/app/utils.py` → `normalize_phone()`
- Voice transcription: `backend/app/services/transcription.py` (Gemini)
- Patient registration: `POST /api/patients/register` in `backend/app/api/patients.py`
- Safety rules: `backend/app/services/safety.py`
- Redis session state + PostgreSQL persistence

**What does not exist yet:**

- Webhook routes (`GET` verification + `POST` handler)
- WhatsApp payload parser and outbound message sender
- `X-Hub-Signature-256` verification
- Background job queue for async processing
- Patient lookup/creation by WhatsApp `from` phone (without `X-Patient-Id`)
- WhatsApp-specific onboarding state ("What should I call you?")
- Media download for inbound voice notes

---



## Before you start — phone number checklist

For `+234 812 261 5453` (E.164: `+2348122615453`):


| Requirement                            | Why                                              |
| -------------------------------------- | ------------------------------------------------ |
| You **own** the number                 | Meta verifies via SMS or voice OTP               |
| It can **receive SMS or a call**       | Required during registration                     |
| You have a **Meta Business Portfolio** | Required for production                          |
| You understand **number mode**         | API-only vs Business App coexistence (see below) |




### Personal WhatsApp vs Business App vs API-only

**Original draft said:** delete personal WhatsApp before registering.

**Corrected:**

1. **Personal WhatsApp (Messenger app):** You cannot run personal WhatsApp and Cloud API on the same number in the usual setup. For a dedicated API number, you typically **deregister** the number from the personal app first, then register it in WhatsApp Manager.
2. **WhatsApp Business App + Cloud API (Coexistence):** Meta supports using the **same number** on both the **WhatsApp Business App** and **Cloud API** via the official **Coexistence** onboarding flow (Embedded Signup → "Connect a WhatsApp Business app"). Requirements include WhatsApp Business App **v2.24.17+**, a linked Facebook Page, and scanning a QR code during setup. **Verify Nigeria eligibility** in [Meta's onboarding docs](https://developers.facebook.com/docs/whatsapp/embedded-signup/custom-flows/onboarding-business-app-users) before assuming coexistence.
3. **For Joy (API-first, fully automated):** Prefer **API-only** registration unless you explicitly need humans replying from the Business App on the same number. Coexistence adds sync complexity (`smb_message_echoes` webhooks, 20 mps throughput cap when on both platforms).

**Nigerian mobile:** `08122615453` normalizes to `+2348122615453` via the existing `normalize_phone()` helper — reuse it for webhook `from` values.

---



## Phase 1 — Meta Business setup (Day 1)



### Step 1: Create Meta Business Portfolio

1. Go to [business.facebook.com](https://business.facebook.com)
2. Create a **Business Portfolio** (e.g. "Rehabify")
3. Add business details — legal name, address, website (`physioaroundme.com` helps trust signals)



### Step 2: Create a Meta Developer app

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. **My Apps → Create App**
3. Choose **Business** type
4. Name it e.g. `Rehabify Joy`
5. Link it to your Business Portfolio



### Step 3: Add WhatsApp product

1. In the app dashboard → **Add Product → WhatsApp**
2. Meta provides a **test phone number** and **temporary access token** immediately
3. You can test webhooks before registering your real number

**Note:** Temporary developer tokens expire in ~24 hours. Use them only for initial webhook testing.



test phone number ID: 1177525952116556  
**WhatsApp Business Account ID: 1833662744464815**

**Temp Access Token: EAAOFisEEJuABRxOnydrv81bNvJNZCnQ99xhJg4WXu0nG0MAXS1N7M0QEs4vRmXS8vZCd2z3zqvFoq4sprkiKtcg7RdCZAZAkvWqPReEIESD2TgNruUrbKHD8Qn5yYElFke68DQZCch2GDSG3kYnvbTP7y7PkQlSW5d4HXUSvPWJhfbA49VdwGJGoAW3YTWbQB5BbN5uvC0bPV01c3RoLZBZAY6YS1i9s4CGb8ZCiY9LoqEMxyGAMZAy2A01KJLZAkp4dZAhFwbHM48yBbqZAlGxpKifdnCRc**  
  
**app secret: e507b2a4fd8706f6b8dbabf3fed61909**

---



## Phase 2 — Register your Nigerian number (Day 1–2)



### Step 4: Add your phone number

1. WhatsApp → **API Setup** (or **Phone Numbers**)
2. Click **Add phone number**
3. Enter: `+2348122615453`
4. Verify via **SMS** or **voice call**
5. Enter the OTP

After verification, Meta assigns a **Phone Number ID** — required for sending messages.

### Step 5: Display name

Submit a **display name** (e.g. `Joy by Rehabify` or `Rehabify`). Meta reviews it (often 24–72 hours). Until approved, messaging may be limited. Subscribe to the `phone_number_name_update` webhook field to track approval.

### Step 6: Permanent access token

Create a **System User** for production:

1. Business Settings → **Users → System Users**
2. Create system user (Admin)
3. **Generate token** with permissions:
  - `whatsapp_business_messaging` (required for messages)
  - `whatsapp_business_management` (required for non-message webhooks and admin)
4. Assign the system user access to your WhatsApp Business Account
5. Save as `WHATSAPP_ACCESS_TOKEN` on Railway — treat it like a password; rotate if leaked

Also record:

- **WhatsApp Business Account ID (WABA ID)** — for subscription troubleshooting
- **Phone Number ID** — for sending messages
- **App Secret** — from App Dashboard → Settings → Basic → **App Secret** (for webhook signature verification)

---



## Phase 3 — Connect your Railway backend (Day 2–3)



### Step 7: Webhook endpoints

Add routes to `backend/app/main.py` (or a new `backend/app/api/whatsapp.py` router).


| Method | Path (example) | Purpose           |
| ------ | -------------- | ----------------- |
| `GET`  | `/webhook`     | Meta verification |
| `POST` | `/webhook`     | Incoming events   |


**Important for this codebase:** Existing routes use the `/api` prefix (`/api/health`, `/api/chat`, etc.). Your Meta callback URL must match the route exactly:

- Option A: mount webhook at `/webhook` (app root, no `/api` prefix) — matches most tutorials
- Option B: mount at `/api/webhook` and register `https://your-app.up.railway.app/api/webhook` in Meta

Railway health check is already at `/api/health` (`backend/railway.toml`).

#### GET verification (one-time setup)

Meta sends:

```
GET /webhook?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=CHALLENGE_STRING
```

Your server must:

1. Check `hub.mode == "subscribe"`
2. Check `hub.verify_token` matches `WHATSAPP_VERIFY_TOKEN`
3. Return `hub.challenge` as **plain text** with HTTP **200**

**Correction:** Return the challenge as a **string**, not `int(challenge)`. FastAPI example:

```python
from fastapi import APIRouter, HTTPException, Query, Response

router = APIRouter(tags=["whatsapp"])

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return Response(content=hub_challenge or "", media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")
```



#### POST handler (production pattern)

```
Meta POSTs JSON
  → Verify X-Hub-Signature-256 (HMAC-SHA256 with App Secret)
  → Enqueue payload (Redis list / background task)
  → Return HTTP 200 immediately (< 3 seconds)
  → Worker: parse message → patient lookup → process_message() → send reply
```

**Do not** call Gemini inside the webhook handler synchronously. That will cause timeouts, retries, and duplicate processing.

#### Signature verification (required)

Every legitimate POST includes `X-Hub-Signature-256: sha256=<hex>`.

```python
import hashlib
import hmac

def verify_signature(app_secret: str, body: bytes, signature_header: str) -> bool:
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)
```

Skip this and anyone who discovers your webhook URL can send fake messages.

### Step 8: Environment variables on Railway

```env
# Required
WHATSAPP_ACCESS_TOKEN=your_permanent_system_user_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_VERIFY_TOKEN=any_random_string_you_choose
WHATSAPP_APP_SECRET=your_meta_app_secret

# Recommended
WHATSAPP_GRAPH_API_VERSION=v25.0
WHATSAPP_BUSINESS_ACCOUNT_ID=your_waba_id

# Already required by Joy
GEMINI_API_KEY=...
DATABASE_URL=...
REDIS_URL=...
```

Add these to `backend/app/config.py` with the same `pydantic-settings` pattern used for Gemini and bucket config.

### Step 9: Register webhook in Meta

1. WhatsApp → **Configuration → Webhook**
2. **Callback URL:** `https://your-railway-backend.up.railway.app/webhook` (or `/api/webhook` if you chose that)
3. **Verify token:** same as `WHATSAPP_VERIFY_TOKEN`
4. Click **Verify and Save**
5. Subscribe to webhook fields:
  - `messages` (required — inbound messages + delivery status)
  - `phone_number_name_update` (recommended — display name approval)
  - `message_template_status_update` (recommended — template approval tracking)

Your backend must be **live and reachable over HTTPS** before Meta can verify.

**Troubleshooting:** If verification succeeds but no POST events arrive, explicitly subscribe the app to your WABA:

```
POST /{WABA_ID}/subscribed_apps
```

Then confirm with `GET /{WABA_ID}/subscribed_apps`. See [Meta webhooks docs](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/set-up-webhooks).

### Step 10: Send message utility

**Correction:** Use a current Graph API version (e.g. `v25.0`), not `v21.0`.

```
POST https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages
Authorization: Bearer {ACCESS_TOKEN}
Content-Type: application/json

{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "+2348122615453",
  "type": "text",
  "text": { "body": "Hi! My name is Joy..." }
}
```

Notes:

- `PHONE_NUMBER_ID` is the **business** phone number ID from Meta, not the patient's number
- `to` is the **patient's** WhatsApp number. Meta's 2026 docs use `+` prefix in examples
- Sending only **accepts** the request; delivery status comes via webhook `statuses` events

---



## Phase 4 — Map WhatsApp to the existing Joy flow (Day 3–5)



### How WhatsApp users become patients

On web, `OnboardingModal` collects name + phone and stores `patient_id` in `localStorage`. On WhatsApp, the phone is automatic from the webhook `from` field (digits, no `+` in payload — e.g. `"2348122615453"`).

Suggested flow:

```
Inbound WhatsApp message from webhook (messages[].from)
    ↓
normalized = normalize_phone(from)   # reuse backend/app/utils.py
    ↓
Look up Patient by phone_number in Postgres
    ↓
If new and no display_name captured yet
    → Joy asks: "What should I call you?"
    → Store answer via register/upsert logic (reuse patients.py patterns)
    ↓
Resolve or create ChatSession for this patient + channel
    ↓
process_message(db, patient, text, session_id)   # existing chat_service.py
    ↓
Send reply via Graph API messages endpoint
```

**Implementation notes for this codebase:**

- Reuse `normalize_phone()` and `POST /api/patients/register` logic, but call it from a service function — not over HTTP
- Web uses `X-Patient-Id`; WhatsApp must resolve patient by phone internally
- Add a **channel** concept or separate session key prefix (`whatsapp:{patient}:{session}`) if you need to isolate web vs WhatsApp history
- Fix the existing session ownership check in `chat_service.py` before production: session lookup should verify `ChatSession.patient_id == patient.id`



### Mapping webhook payload to Joy

Inbound text message structure (simplified):

```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "changes": [{
      "field": "messages",
      "value": {
        "messaging_product": "whatsapp",
        "metadata": { "phone_number_id": "..." },
        "contacts": [{ "profile": { "name": "..." }, "wa_id": "234..." }],
        "messages": [{
          "from": "2348122615453",
          "id": "wamid.xxx",
          "timestamp": "1749416383",
          "type": "text",
          "text": { "body": "My back hurts" }
        }]
      }
    }]
  }]
}
```

Handle:

- **Batched entries** — `entry` and `changes` are arrays; loop all of them
- **Status updates** — same `messages` field webhook includes `statuses[]` for sent/delivered/read/failed; ignore or log separately
- **Deduplication** — use `messages[].id` (wamid). Meta retries for up to **7 days** on non-200 responses; same event may arrive multiple times. Use Redis `SETNX` or a DB unique index



### Voice notes on WhatsApp

**Correction:** WhatsApp does not send a direct download URL in the webhook. It sends a **media ID**.

Flow:

```
User sends voice note (type: "audio")
    ↓
Webhook: messages[].audio.id = "<MEDIA_ID>"
    ↓
GET https://graph.facebook.com/v25.0/<MEDIA_ID>
    Authorization: Bearer {ACCESS_TOKEN}
    → returns { "url": "https://...", "mime_type": "audio/ogg", ... }
    ↓
GET <url> with Authorization: Bearer {ACCESS_TOKEN}
    → raw audio bytes
    ↓
Optional: upload_audio() to bucket (reuse services/storage.py)
    ↓
transcribe_audio() (reuse services/transcription.py — Gemini)
    ↓
process_message(..., message_type="voice", audio_url=...)
```

WhatsApp voice is typically **OGG/Opus**, not WebM. The existing transcription service should accept the MIME type returned by Meta.

### Interactive messages (future)

WhatsApp supports buttons, lists, and flows. Joy currently returns plain text. Consider WhatsApp interactive messages for triage choices later — not required for v1.

---



## Phase 5 — Meta rules you must know



### Customer service window (24 hours)

**Terminology update:** Meta calls this the **customer service window** (CSW), not "messaging window."

- **Within 24h** of the user's last inbound message → send **non-template** (free-form) messages freely — this is how Joy triage works
- **After 24h** with no new user message → you can only send **approved message templates**

For daily exercise reminders (from the product brief), create **utility** templates such as:

```
Good morning {{1}}, time for your exercises today. Reply when you're done.
```

Submit in WhatsApp Manager → **Message Templates**. Review typically takes 24–48 hours.

### Pricing (corrected — July 2025 onward)

**Original draft framed this as conversation-based pricing. That model was retired July 1, 2025.**

Current model (per [Meta pricing docs](https://developers.facebook.com/docs/whatsapp/pricing/)):


| Message type                                                       | Cost                                                        |
| ------------------------------------------------------------------ | ----------------------------------------------------------- |
| Non-template replies (text, image, audio, etc.) inside an open CSW | **Free**                                                    |
| Template messages — marketing                                      | Charged per delivered message (varies by recipient country) |
| Template messages — utility                                        | Free inside CSW; charged outside CSW                        |
| Template messages — authentication                                 | Charged per delivered message                               |
| Service messages (user-initiated conversations)                    | **Free** since November 2024                                |


Nigeria (`+234`) has standalone rate card entries. Check Meta's rate card for current NGN/USD rates.

**For Joy triage:** User messages first → CSW opens → Joy's free-form Gemini replies are **free**. Proactive reminders after 24h silence need **approved utility templates** (may incur cost outside CSW).

### Business verification

- **Development / low volume:** Test number or unverified business may work initially
- **Production / scale:** Complete **Business Verification** in Meta Business Manager
- **Healthcare / Nigeria:** Align with **NDPR** — capture consent for WhatsApp communication and AI-assisted triage; the product brief already flags this



### App mode

Some webhook behavior differs between **Development** and **Live** app mode. Move to **Live** before production pilot. Complete App Review if you need advanced permissions as a solution provider.

### Webhook reliability


| Rule               | Detail                                                                      |
| ------------------ | --------------------------------------------------------------------------- |
| Response time      | Return HTTP **200** immediately; target **< 3 seconds**                     |
| Retries            | Meta retries failed deliveries for up to **7 days** with backoff            |
| Delivery guarantee | **At-least-once** — duplicates are normal; dedupe by wamid                  |
| Ordering           | **Not guaranteed** — events may arrive out of order                         |
| Payload limit      | Up to **3 MB** per webhook                                                  |
| mTLS (optional)    | If enabled, note Meta's CA certificate update deadline (**March 31, 2026**) |


---



## Phase 6 — Go live checklist

```
□ Meta Business Portfolio created
□ Developer app with WhatsApp product added
□ +2348122615453 verified (number mode chosen: API-only or Coexistence)
□ Display name submitted and approved
□ Permanent system user token generated
□ WHATSAPP_APP_SECRET configured
□ Webhook GET verification passing
□ Webhook POST handler with X-Hub-Signature-256 validation
□ Async processing (queue or background task) — no Gemini in webhook handler
□ Message deduplication by wamid (messages[].id)
□ Patient lookup/creation by phone (normalize_phone)
□ WhatsApp onboarding for display_name on first contact
□ Wire to process_message() in chat_service.py
□ Outbound send via Graph API messages endpoint
□ Voice: media ID → download → transcribe_audio() → process_message()
□ Test: send "Hello" on WhatsApp → Joy replies
□ Utility templates submitted for proactive reminders
□ Session ownership fix in chat_service.py (patient_id check)
□ CORS not needed for webhook (Meta server-to-server)
□ Railway callback URL uses HTTPS and matches registered path exactly
```

---



## Timeline estimate


| Phase                                     | Time                                     |
| ----------------------------------------- | ---------------------------------------- |
| Meta Business + Developer app             | 1–2 hours                                |
| Register +2348122615453                   | ~30 min (+ display name review 1–3 days) |
| Webhook + echo bot on Railway             | 1–2 days                                 |
| Signature verification + async queue      | 0.5–1 day                                |
| Wire to existing Joy (Gemini, Redis, DB)  | 2–3 days                                 |
| WhatsApp voice note download + transcribe | 1 day                                    |
| Utility templates for proactive reminders | 1–3 days review                          |
| Business verification (if needed)         | 3–14 days                                |


---



## Recommended build order (for this codebase)

1. **Config** — Add WhatsApp env vars to `backend/app/config.py`
2. `GET /webhook` **+** `POST /webhook` — Echo bot with signature verification
3. **Async worker** — Redis queue or `asyncio.create_task` with error handling
4. **WhatsApp adapter** — Parse Meta payload → patient by phone → `process_message()`
5. **Outbound sender** — Thin `send_whatsapp_text(to, body)` wrapper around Graph API
6. **Display name onboarding** — Redis flag for "awaiting_name" on new patients
7. **Voice** — Media download + existing `transcribe_audio()` + `process_message()`
8. **Message templates** — Utility templates for daily nudges (product brief Phase 2)
9. **Hardening** — Dedup, session ownership fix, delivery status logging

**First milestone:** Phase 1 only — webhook verified on Railway, echo bot replies "pong" to any text. Proves the pipe before wiring full Joy logic.

---



## Using +234 812 261 5453 — summary

This number is valid for WhatsApp Cloud API if:

1. You control it and can receive OTP
2. You have chosen number mode (API-only deregister, or Business App coexistence)
3. You register it in WhatsApp Manager and obtain Phone Number ID
4. Your Railway webhook is live, HTTPS, signature-verified, and async
5. You do **not** need a third-party BSP — Meta Cloud API is direct, matching the product brief

---



## References

- [Set up webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/set-up-webhooks)
- [Send messages](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-messages)
- [Messages API reference](https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages)
- [Pricing](https://developers.facebook.com/docs/whatsapp/pricing/)
- [Coexistence / Business App onboarding](https://developers.facebook.com/docs/whatsapp/embedded-signup/custom-flows/onboarding-business-app-users)
- Joy backend entry: `backend/app/main.py`
- Joy chat pipeline: `backend/app/services/chat_service.py`

