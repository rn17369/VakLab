# VakLab - Voice AI Agent for Health Reward Campaign

Enterprise-grade Voice AI Agent Framework built with PGoogle Cloud AI, Pipecat,  and Twilio for automated outbound calling campaigns.

## 🎯 Overview

VakLab is an intelligent Voice AI agent that makes outbound calls to engage members in health rewards programs. The agent uses:
- **Google Gemini 3 Flash** for natural language understanding and generation
- **Google Cloud Speech-to-Text** for real-time transcription
- **Google Cloud Text-to-Speech** for natural voice synthesis
- **Pipecat AI** for real-time audio pipeline processing
- **Twilio** for telephony infrastructure

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              VakLab Architecture                             │
└─────────────────────────────────────────────────────────────────────────────┘

                                    ┌─────────────┐
                                    │   Member    │
                                    │   Phone     │
                                    └──────┬──────┘
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │        Twilio          │
                              │   (Voice Platform)     │
                              └────────────┬───────────┘
                                           │ WebSocket
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Server (Port 8000)                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────────────────────────────────────┐ │
│  │  /twilio/       │    │              Pipecat Pipeline                   │ │
│  │  outbound-call  │───▶│                                                 │ │
│  │  (Trigger)      │    │  ┌─────────┐   ┌─────────┐   ┌─────────────┐   │ │
│  └─────────────────┘    │  │ Google  │   │ Google  │   │   Google    │   │ │
│                         │  │  STT    │──▶│  LLM    │──▶│    TTS      │   │ │
│  ┌─────────────────┐    │  │(Speech) │   │(Gemini) │   │  (Voice)    │   │ │
│  │  /twilio/       │    │  └─────────┘   └─────────┘   └─────────────┘   │ │
│  │  voice-entry    │    │                     │                          │ │
│  │  (TwiML)        │    │              ┌──────┴──────┐                   │ │
│  └─────────────────┘    │              │   Tools     │                   │ │
│                         │              ├─────────────┤                   │ │
│  ┌─────────────────┐    │              │ • send_email│                   │ │
│  │  /twilio/       │    │              │ • end_call  │                   │ │
│  │  stream         │◀──▶│              └─────────────┘                   │ │
│  │  (WebSocket)    │    │                                                 │ │
│  └─────────────────┘    └─────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │     PostgreSQL DB      │
                              │  (Member Data Store)   │
                              └────────────────────────┘
```

---

## 📞 Call Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Outbound Call Flow                                  │
└──────────────────────────────────────────────────────────────────────────────┘

    ┌─────────┐          ┌─────────┐          ┌─────────┐          ┌─────────┐
    │  START  │          │ State 1 │          │ State 2 │          │ State 3 │
    │         │─────────▶│  HOOK   │─────────▶│  VALUE  │─────────▶│ ENROLL  │
    └─────────┘          └─────────┘          └─────────┘          └─────────┘
                              │                    │                    │
                              │                    │                    │
    ┌─────────────────────────┴────────────────────┴────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   STATE 1: THE HOOK                                                         │
│   ────────────────                                                          │
│   Agent: "Hi {name}, I'm Metna. I'm calling to help you get rewarded       │
│           for your healthy habits. Do you have a moment?"                   │
│                                                                              │
│   User: "Yes" ──────────────────────────────▶ Move to State 2               │
│   User: "No"  ──────────────────────────────▶ "No problem! Have a           │
│                                                 healthy day!" → end_call()  │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   STATE 2: THE VALUE PROP                                                   │
│   ───────────────────────                                                   │
│   Agent: "It's simple! You earn rewards—like gift cards—for things         │
│           you already do, like daily walks or annual checkups.              │
│           Would you like to enroll today?"                                  │
│                                                                              │
│   User: "Yes" / "Tell me more" ─────────────▶ Move to State 3               │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   STATE 3: THE ENROLLMENT                                                   │
│   ───────────────────────                                                   │
│   Agent: "That's wonderful! I'll send details to your email:               │
│           {email}. Does that sound good?"                                   │
│                                                                              │
│   User: "Yes" ──────────────────────────────▶ send_enrollment_email()       │
│                                               "Excellent! You're all set!"  │
│                                               "Anything else?"              │
│                                                                              │
│   User: "No, I'm good" ─────────────────────▶ "Thank you! Have a            │
│                                                 wonderful day!" → end_call() │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Sequence Diagram

```
┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐
│  User  │     │ Twilio │     │FastAPI │     │Pipecat │     │ Google │     │  SMTP  │
│ Phone  │     │        │     │ Server │     │Pipeline│     │ Cloud  │     │ Server │
└───┬────┘     └───┬────┘     └───┬────┘     └───┬────┘     └───┬────┘     └───┬────┘
    │              │              │              │              │              │
    │              │   POST /outbound-call       │              │              │
    │              │◀─────────────┤              │              │              │
    │              │              │              │              │              │
    │  Ring Ring   │  Create Call │              │              │              │
    │◀─────────────┤◀─────────────┤              │              │              │
    │              │              │              │              │              │
    │   Answers    │   TwiML      │              │              │              │
    │─────────────▶│─────────────▶│              │              │              │
    │              │              │              │              │              │
    │              │   WebSocket Connect         │              │              │
    │              │─────────────▶│─────────────▶│              │              │
    │              │              │              │              │              │
    │              │              │  Start Pipeline              │              │
    │              │              │─────────────▶│              │              │
    │              │              │              │              │              │
    │              │              │              │  LLM Request │              │
    │              │              │              │─────────────▶│              │
    │              │              │              │              │              │
    │              │              │              │  "Hi Raju..."|              │
    │◀─────────────┼──────────────┼──────────────┼◀─────────────┤              │
    │              │              │              │   TTS Audio  │              │
    │              │              │              │              │              │
    │   "Yes"      │              │              │              │              │
    │─────────────▶│─────────────▶│─────────────▶│              │              │
    │              │              │              │   STT Text   │              │
    │              │              │              │─────────────▶│              │
    │              │              │              │              │              │
    │              │              │              │   LLM "Yes"  │              │
    │              │              │              │─────────────▶│              │
    │              │              │              │              │              │
    │              │              │              │ Tool: email  │              │
    │              │              │              │─────────────▶│─────────────▶│
    │              │              │              │              │   ✉️ Sent    │
    │              │              │              │◀─────────────┼──────────────│
    │              │              │              │              │              │
    │  "You're all set!"          │              │              │              │
    │◀─────────────┼──────────────┼──────────────┼◀─────────────┤              │
    │              │              │              │              │              │
    │              │              │              │ Tool: end_call              │
    │              │              │              │─────────────▶│              │
    │              │              │              │              │              │
    │   Hangup     │              │              │              │              │
    │◀─────────────┤              │              │              │              │
    │              │              │              │              │              │
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI + Pipecat AI |
| **LLM** | Google Gemini 3 Flash Preview |
| **Speech-to-Text** | Google Cloud STT |
| **Text-to-Speech** | Google Cloud TTS (Journey-F voice) |
| **Voice Activity Detection** | Silero VAD |
| **Telephony** | Twilio Voice |
| **Database** | PostgreSQL |
| **Tunnel** | ngrok |

---

## 📋 Prerequisites

1. **Python 3.12+**
2. **Docker & Docker Compose** (for PostgreSQL)
3. **ngrok account** (for public URL tunnel)
4. **Google Cloud Account** with:
   - Cloud Speech-to-Text API enabled
   - Cloud Text-to-Speech API enabled
   - Gemini API key
   - Service account JSON credentials
5. **Twilio Account** with:
   - Account SID
   - Auth Token
   - Phone number

---

## 🚀 Setup Instructions

### Step 1: Clone and Setup Environment

```bash
# Navigate to project directory
cd /path/to/gcp_hackthon

# Create virtual environment
python3.12 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Pipecat with Google and Silero extras
pip install "pipecat-ai[google,silero]"
```

### Step 2: Configure Environment Variables

Create a `.env` file in the project root:

```env
# Google Cloud
GOOGLE_API_KEY=your_google_api_key
GOOGLE_GENAI_USE_VERTEXAI=0

# Database
DB_HOST=localhost
DB_NAME=outbound_agent_db
DB_USER=user
DB_PASSWORD=password

# SMTP (for sending emails)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Twilio
TWILIO_SID=your_twilio_account_sid
TWILIO_AUTH=your_twilio_auth_token
TWILIO_NUMBER=+1234567890

# Domain (ngrok URL - update after starting ngrok)
DOMAIN=https://your-ngrok-url.ngrok-free.app
```

### Step 3: Setup Google Cloud Credentials

1. Create a service account in Google Cloud Console
2. Download the JSON credentials file
3. Place it in the project root
4. Update the path in `routers/pipe_bot.py` if needed

### Step 4: Start PostgreSQL Database

```bash
# Start the database container
docker compose up -d

# Verify it's running
docker ps
```

The database will be initialized with seed data from `db-init/init.sql`.

### Step 5: Start ngrok Tunnel

```bash
# In a new terminal
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`) and update:
1. `.env` file: `DOMAIN=https://abc123.ngrok-free.app`

### Step 6: Start the Server

```bash
# Activate virtual environment
source venv/bin/activate

# Start FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📱 Making Outbound Calls

### Trigger a Call

```bash
curl -X POST http://localhost:8000/twilio/outbound-call
```

This will:
1. Look up the first member in `campaign_target_member_call_list`
2. Initiate an outbound call via Twilio
3. Connect the AI agent when the call is answered

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/twilio/outbound-call` | POST | Trigger outbound call |
| `/twilio/voice-entry` | POST | Twilio webhook for TwiML |
| `/twilio/stream` | WebSocket | Audio streaming endpoint |
| `/twilio/callback` | POST | Call status callbacks |

---

## 📁 Project Structure

```
gcp_hackthon/
├── main.py                     # FastAPI application entry point
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # PostgreSQL container config
├── .env                        # Environment variables
├── cool-furnace-*.json         # Google Cloud credentials
│
├── agents/
│   └── outbound_agent/
│       ├── __init__.py
│       ├── agent.py            # MetnaAgent (LLM instructions)
│       └── tools.py            # Tool functions (email, end_call)
│
├── routers/
│   ├── __init__.py
│   ├── health.py               # Health check endpoint
│   ├── outbound_twillio.py     # Twilio webhooks & call handling
│   └── pipe_bot.py             # Pipecat pipeline configuration
│
├── utils/
│   ├── __init__.py
│   ├── audio.py                # Audio utilities
│   ├── db.py                   # Database connection
│   ├── env.py                  # Environment helpers
│   └── security.py             # Security utilities
│
├── entities/
│   └── twilio.py               # Twilio entity models
│
└── db-init/
    └── init.sql                # Database initialization script
```

---

## 🔧 Configuration Options

### Voice Configuration (pipe_bot.py)

```python
# Text-to-Speech Voice
tts = GoogleTTSService(
    voice_id="en-US-Journey-F",  # Female voice
    sample_rate=8000
)

# Voice Activity Detection
vad_analyzer=SileroVADAnalyzer(
    params=VADParams(stop_secs=0.5)  # Wait 0.5s after speech stops
)
```

### LLM Configuration (agent.py)

```python
model="gemini-3-flash-preview",
planner=BuiltInPlanner(
    thinking_config=types.ThinkingConfig(
        thinking_budget=0  # Minimal thinking for lower latency
    )
)
```

---

## 🧪 Testing

### Test Email Function

```bash
python -c "
from agents.outbound_agent.tools import send_enrollment_email
result = send_enrollment_email('test@example.com', 'TestUser')
print(f'Email sent: {result}')
"
```

### Test Database Connection

```bash
python -c "
from utils.db import get_db_connection
conn = get_db_connection()
print('Connected!' if conn else 'Failed!')
if conn: conn.close()
"
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| No audio on call | Check TTS service credentials path |
| LLM not responding | Verify GOOGLE_API_KEY in .env |
| WebSocket disconnects | Ensure ngrok is running and URL is updated |
| Email not sending | Verify SMTP credentials (use App Password for Gmail) |
| Database connection failed | Run `docker compose up -d` |

---

## 📝 Logs

Monitor server logs for debugging:

```bash
# Server logs show:
# - Call initiation
# - WebSocket connections
# - STT transcriptions
# - LLM responses
# - TTS generation
# - Tool function calls
```

Example log output:
```
INFO: Starting Pipecat bot for call CA123...
INFO: Member data: {'member_first_name': 'Raju', ...}
INFO: [EVENT] Pipecat bot connected for Raju
INFO: [GREETING] Triggered LLM to generate greeting
DEBUG: GoogleTTSService: Generating TTS [Hi Raju, I'm Metna...]
INFO: [TOOL] send_enrollment_email called for Raju at raju@example.com
INFO: ✓ Email successfully sent to raju@example.com
INFO: [TOOL] end_call triggered - ending conversation
```

---

## 📄 License

MIT License

---

## 👥 Contributors

- VakLab Team

---

## 🔗 Resources

- [Pipecat AI Documentation](https://github.com/pipecat-ai/pipecat)
- [Google Cloud Speech-to-Text](https://cloud.google.com/speech-to-text)
- [Google Cloud Text-to-Speech](https://cloud.google.com/text-to-speech)
- [Twilio Voice API](https://www.twilio.com/docs/voice)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
