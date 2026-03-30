# AI-First Airtasker Clone for India 🚀

An AI-native peer-to-peer services marketplace optimized for the Indian gig economy. This platform uses AI to reduce friction, eliminate language barriers, and ensure fair pricing.

## 🌟 Core Features

- **AI Task Parsing (For Posters):**
  - **Voice-to-Task:** Record audio in native languages to auto-generate structured tasks.
  - **Image-to-Task:** Upload photos for Vision AI to analyze and suggest job descriptions.
  - **Smart Budgeting:** AI suggests a fair price range based on historical data.

- **AI Matchmaking & Vetting (For Taskers):**
  - **Skill Extraction:** AI extracts skills from voice chats or past work photos.
  - **Hyper-Personalized Feed:** Precise task pushing based on location, performance, and skills.

- **AI-Mediated Communication:**
  - **Real-time Translation Chat:** Seamless cross-language communication.
  - **Auto-Negotiator Bot:** Mediates fair pricing automatically.

- **Trust & Safety:**
  - **Automated KYC:** Facial recognition matching with Aadhaar/PAN.
  - **Outcome Verification:** Vision AI verifies "before" and "after" photos before escrow release.

## 💻 Tech Stack
- **Backend:** Python, FastAPI
- **Database:** PostgreSQL (with Alembic for migrations)
- **AI Models:** Gemini 2.0 Flash & Pro Vision, Bhashini API
- **Payments & Identity:** Razorpay (Escrow), DigiLocker API

## 🛠 Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/muskan-424/air-tasker.git
   cd air-tasker
   ```
2. **Setup Backend:**
   Navigate into the `backend_fastapi` directory, configure your `.env` based on `.env.example`, and install the dependencies from `requirements.txt`.
