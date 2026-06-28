**JOY**

**The AI Recovery Companion Powering Rehabify**

_Product Brief - Investor Sample_

Rehabify | physioaroundme.com | Confidential

# **What Is Joy?**

Joy is Rehabify's AI recovery companion - a conversational AI assistant that lives on WhatsApp and guides every patient through their physiotherapy journey, from the first clinical triage conversation to daily exercise adherence at home.

Joy is not a chatbot bolted onto a booking platform. Joy is the clinical intelligence layer that powers three core Rehabify products: Rehabify Predict (AI triage), the patient-facing recovery companion (daily engagement and adherence), and Rehabify Companion (AI computer vision form correction).

**In one line:** Joy is the AI that makes physiotherapy in Nigeria accessible, safe, and effective - delivered entirely through WhatsApp, the app every Nigerian already uses.

# **Why Joy Matters**

Nigeria has fewer than 2,500 registered physiotherapists serving a population of over 220 million people. Even with a fully functioning marketplace connecting patients to physios, there are not enough physiotherapists to deliver the volume of hands-on care the country needs. Joy is Rehabify's answer to that capacity gap - extending the reach of every physiotherapist on the platform without requiring more of their time.

| **80%**<br><br>of Nigerians needing physio never get it | **<2,500**<br><br>physiotherapists in Nigeria | **24/7**<br><br>Joy is available on WhatsApp |
| ------------------------------------------------------- | --------------------------------------------- | -------------------------------------------- |

# **What Joy Does**

## **1\. Clinical Triage - Rehabify Predict**

Before a patient sees any physiotherapist, Joy runs a 3-5 minute conversational clinical screen. Adaptive questioning identifies red flags, stratifies risk, and generates a structured clinical summary shared with the matched physiotherapist before the first session.

- Risk stratification: Low / Medium / High, with hard-coded safety overrides for red flag symptoms
- Supports English, with phased rollout of Yoruba, Igbo, and Hausa
- Generates a structured clinical handoff - not just a booking, a clinical brief

## **2\. Daily Recovery Companion**

Between physiotherapy sessions, Joy keeps the patient engaged and on track:

- Sends daily exercise reminders at a time the patient chooses
- Logs exercise completion via simple WhatsApp replies
- Tracks adherence and flags drop-off to the physiotherapist automatically
- Answers patient questions and escalates clinical concerns appropriately
- Coordinates communication between patient, physiotherapist, family, and referring doctor

## **3\. AI Form Correction - Rehabify Companion**

Patients record themselves performing prescribed exercises. Joy's computer vision model analyses body landmarks and joint angles against the correct form profile, delivering feedback within seconds - entirely via WhatsApp.

- Pose estimation runs on standard smartphone cameras - no specialist equipment required
- Feedback delivered conversationally: what the patient did well, and exactly what to correct
- Significant form errors are flagged to the physiotherapist's dashboard automatically

## **4\. Voice and Local Language - Joy Speaks Nigeria**

Most digital health products in Nigeria assume English literacy and text-based interaction. Joy does not. Voice and local language support are not an add-on - they are core to reaching the patients who are currently excluded from physiotherapy access entirely: elderly patients, patients with limited literacy, and patients who are simply more comfortable speaking than typing.

- Patients can send voice notes describing symptoms during triage, reporting on exercise sessions, or asking questions - exactly how Nigerians already communicate on WhatsApp
- Joy understands and responds in Yoruba and Igbo today, with Hausa support in active development
- Physiotherapists also receive voice note session reports - speaking their clinical summary after a visit rather than typing it - which Joy transcribes and structures automatically
- Voice is routed intelligently: English-dominant speech goes through Whisper, Yoruba and local dialect speech goes through Intron Health's Sahara-v2 - a Nigerian speech AI company built specifically for African accents and languages

**Why this matters for investors:** No competitor - Nigerian or international - has solved voice-based AI healthcare interaction in Yoruba, Igbo, or Hausa at this depth. This is a genuine, defensible first. It is also the single biggest lever for reaching the patients who need physiotherapy most but are least likely to engage with a text-only product: older adults, rural patients, and lower-literacy populations who represent a large share of Nigeria's undiagnosed and untreated MSK and neurological burden.

# **Why WhatsApp**

WhatsApp is the most used application in Nigeria, across every income bracket and every region. Building Joy on WhatsApp rather than a standalone app means zero download friction, instant familiarity, and a channel patients already trust for important communication.

**Design Principle** Joy meets the patient where they already are. No new app to learn. No download. No login. Just a WhatsApp conversation with an assistant that knows their condition, their physiotherapist, and their progress.

# **Joy in Action - Sample Conversation**

The following is a representative exchange showing Joy guiding a patient through a daily exercise check-in and form correction.

**Joy** 8:02 AM

Good morning Tunde. Time for your back exercises. 3 sets today, takes about 12 minutes.

8:18 AM

Done! Should I send a video?

**Joy** 8:18 AM

Yes please. Record your second set and send it here. I'll check your form right away.

**Joy** 8:21 AM

Great effort! One thing: your left knee is rotating inward on the squat. Try turning your toes slightly outward. I've flagged this for Dr Adaeze to review too.

# **Technology Stack**

Joy is built on proven, production-grade infrastructure, chosen for reliability, cost efficiency, and fit with Nigeria's connectivity environment.

| **Layer**               | **Technology**                                                                                                       |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Messaging channel**   | Meta WhatsApp Business Cloud API, direct integration, no third-party reseller                                        |
| **Conversation AI**     | GPT-4o or Claude 3.5 Sonnet, evaluated for clinical accuracy, dialect handling, and cost                             |
| **Clinical logic**      | Versioned system prompt authored by Rehabify's clinical team, defining triage rules and red flag criteria            |
| **Safety layer**        | Hard-coded keyword override for red flag symptoms, does not rely on the AI model alone for critical safety decisions |
| **Voice transcription** | OpenAI Whisper (English) plus Intron Sahara-v2 (Yoruba and local dialect)                                            |
| **Computer vision**     | MediaPipe Pose, lightweight pose estimation, runs on standard smartphone video                                       |
| **Conversation memory** | Redis, stores session context so Joy remembers the conversation without database overhead on every message           |
| **Scheduled messaging** | Celery plus Redis task queue, handles reminders and check-ins with retry logic and monitoring                        |
| **Backend API**         | FastAPI (Python), async, fast, built for AI integration                                                              |
| **Database**            | PostgreSQL via Supabase, relational structure for clinical data, built-in auth and row-level security                |
| **Frontend**            | Next.js, physiotherapist and patient dashboards, Joy activity feed                                                   |
| **Hosting**             | Vercel (frontend) plus Railway (backend), low DevOps overhead, scales with usage                                     |

# **What's Required to Build Joy**

## **Team**

- 1 backend engineer (Python / FastAPI), owns the AI integration and WhatsApp webhook logic
- 1 frontend engineer (Next.js), owns the physiotherapist and patient dashboards
- 1 clinical lead, authors and maintains the triage system prompt and safety protocols (already filled by Rehabify's founding physiotherapist)
- Part-time DevOps support for deployment and monitoring as usage scales

## **Third-party services and approvals**

- Meta WhatsApp Business Cloud API account and approved message templates
- OpenAI or Anthropic API access for conversational AI and tool-use (function calling)
- OpenAI Whisper API access for voice transcription
- Intron Health partnership discussion for Yoruba and local dialect voice support
- Supabase project for database, auth, and storage
- Paystack integration for in-conversation payment links

## **Clinical and regulatory**

- Clinical system prompt developed and reviewed by Rehabify's physiotherapy team
- Red flag criteria and escalation pathway defined and tested before launch
- NDPR (Nigeria Data Protection Regulation) compliance for patient data handling
- Consent capture flow for WhatsApp communication and AI-assisted triage

## **Estimated build timeline**

| **Phase**      | **Scope**                                                                                                             |
| -------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Weeks 1-4**  | WhatsApp webhook, basic conversation flow, triage system prompt v1, safety override logic                             |
| **Weeks 5-8**  | Exercise reminders, adherence logging, dashboard integration, Celery scheduled messaging                              |
| **Weeks 9-12** | Computer vision form correction (MediaPipe integration), voice transcription, pilot testing with first patient cohort |

# **The Opportunity**

Joy is the layer that makes Rehabify defensible. Anyone can build a booking marketplace. Nobody else in Nigeria has an AI companion that triages patients clinically, keeps them engaged daily, and verifies their exercise form, all without requiring a new app, a strong data connection, or English fluency.

Every conversation Joy has, every triage she runs, and every exercise she reviews builds a clinical dataset on MSK and neurological outcomes in Nigerian patients that does not exist anywhere else in the world today. That dataset compounds in value as Rehabify scales, across Nigeria, and eventually into the UK, US, and Canadian diaspora markets.

**JOY - The AI Recovery Companion Powering Rehabify**

physioaroundme.com | <hello@physioaroundme.com> | Confidential - Investor Material