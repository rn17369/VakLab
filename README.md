# VakLab - Voice AI Agent for Preventive Screening Outreach 

Enterprise-grade Voice AI Agent Framework built with PGoogle Cloud AI, Pipecat,  and Twilio for automated outbound calling campaigns.

## 🎯 Overview

VakLab is an intelligent Voice AI agent that makes outbound calls to engage members in Preventive Health Screening. The agent uses:
- **Google Gemini 3 Preview** for natural language understanding and generation
- **Google Cloud Speech-to-Text** for real-time transcription
- **Google Cloud Text-to-Speech** for natural voice synthesis
- **Pipecat AI** for real-time audio pipeline processing
- **Twilio** for telephony infrastructure
- **Live Transcript Dashboard** for real-time call monitoring

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
│  ┌─────────────────┐    │  │(Speech) │   │(Gemini 3) │   │  (Voice)    │   │ │
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
```mermaid
flowchart TD
  Start([Start]) --> Hook["State 1:\nThe Hook"]

  Hook -->|No| EndNo["Respond politely\nend_call()"]
  Hook -->|Yes| Zip["State 2:\nZip Code Verification"]

  Zip -->|Zip matches| Prop["State 3:\nMammogram Value Prop"]
  Zip -->|Not serviced| EndResource["Explain & offer resources\nend_call()"]

  Prop -->|No| EndThank["Thank & end_call()"]
  Prop -->|Yes / Tell me more| Enroll["State 4:\nEnrollment & Action"]

  Enroll -->|Yes| SendEmail["send_enrollment_email(email_address, first_name)"]
  SendEmail --> Confirm["Confirm: 'You're all set!'\n(acknowledge email)"]
  Confirm --> EndDone["end_call()"]

  Enroll -->|No| EndThank
```

---

## 🔄 Sequence Diagram

```
┌──────┐   ┌────────┐   ┌────────┐   ┌────────────┐   ┌──────────┐   ┌────────┐
│User  │   │ Twilio │   │ FastAPI│   │BCSGapAgent │   │ Rebecca  │   │ Tools  │
└──┬───┘   └──┬─────┘   └──┬─────┘   └────┬───────┘   └────┬─────┘   └──┬─────┘
   │           │            │              │               │            │
   │  Answer   │            │              │               │            │
   │──────────▶│            │              │               │            │
   │           │  Webhook   │              │               │            │
   │           │──────────▶│  POST /outbound-call  ──────▶│            │
   │           │            │─────────────▶│ _get_member_data│         │
   │           │            │              │──────────────▶│ instantiate Rebecca
   │           │            │              │               │   run_live │
   │           │            │              │               │──────────▶│
   │           │            │              │  "Hi {first_name}..."       │
   │◀──────────│            │              │◀──────────────│            │
   │  Speech   │            │              │   (TTS/STT via Pipecat)      │
   │  Reply    │            │              │──────────────▶│            │
   │──────────▶│            │              │   (zip code provided)       │
   │           │            │              │──────────────▶│            │
   │           │            │              │  (If enroll)  │ send_enrollment_email
   │           │            │              │──────────────▶│──────────▶│
   │           │            │              │               │   email sent│
   │           │            │              │  end_call()   │──────────▶│
   │   Hangup  │            │              │──────────────▶│            │
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI + Pipecat AI |
| **LLM** | Google Gemini 2.5 Flash |
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
| `/ui` | GET | Live Transcript Dashboard |
| `/ui/transcripts` | WebSocket | Real-time transcript stream |

---

## 📺 Live Transcript Dashboard

VakLab includes a real-time transcript dashboard that shows the conversation as it happens.

### Accessing the Dashboard

1. Start the server (see Setup Instructions)
2. Open your browser and navigate to:
   ```
   http://localhost:8000/ui
   ```

### Features

- **Real-time transcription** — See Rebecca's responses and customer speech live
- **Visual call status** — Green indicator when call is in progress
- **Speaker identification** — Rebecca (AI) on the left in blue, Customer on the right in green
- **Auto-scroll** — Transcript automatically scrolls as new messages appear
- **Call state tracking** — Shows "Call in progress" and "Call complete" banners

### How It Works

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Pipecat       │────▶│   Transcript     │────▶│   WebSocket     │
│   Pipeline      │     │   Manager        │     │   Broadcast     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │   Browser UI    │
                                                 │   Dashboard     │
                                                 └─────────────────┘
```

The dashboard connects via WebSocket and receives:
- `call_started` — When a new call begins (includes customer name)
- `transcript_message` — Customer speech from STT
- `ai_stream_start` / `ai_stream_chunk` / `ai_stream_end` — Rebecca's responses (streamed)
- `call_ended` — When the call completes

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
│       ├── agent.py            # VaklabAgent (Rebecca - LLM instructions)
│       └── tools.py            # Tool functions (email, end_call)
│
├── frontend/
│   └── index.html              # Live Transcript Dashboard UI
│
├── routers/
│   ├── __init__.py
│   ├── health.py               # Health check endpoint
│   ├── outbound_twillio.py     # Twilio webhooks & call handling
│   └── pipe_bot.py             # Pipecat pipeline configuration
│
├── utils/
│   ├── __init__.py
│   ├── db.py                   # Database connection
│   ├── env.py                  # Environment helpers
│   ├── security.py             # Security utilities
│   └── transcript_manager.py   # Real-time transcript broadcasting
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
model="gemini-2.5-flash-lite-preview-06-17",
planner=BuiltInPlanner(
    thinking_config=types.ThinkingConfig(
        thinking_budget=0  # Minimal thinking for lower latency
    )
)
```

---

## 🧪 Testing & Evaluation

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

## 📊 Agent Evaluation Framework

VakLab includes a comprehensive evaluation framework using Google ADK's User Simulation to test the agent against various conversation scenarios.

### Test Scenarios

| # | Scenario | Description |
|---|----------|-------------|
| 0 | Happy Path | User expresses interest, provides zip code, enrolls |
| 1 | Pain Concern | User asks "Does the mammogram hurt?", then enrolls |
| 2 | User Busy | User can't talk now, agent offers to call back |
| 3 | Cost Questions | User asks about cost, procedure duration, then enrolls |
| 4 | User Declines | User politely declines (not interested) |

### Running Evaluations

**Step 1: Export your API key** (required for ADK CLI)
```bash
export GOOGLE_API_KEY=your_api_key_here
```

**Step 2: Run the evaluation**
```bash
adk eval agents/outbound_agent vaklab_eval_set \
    --config_file_path eval/eval_config_stable_with_metrics.json \
    --print_detailed_results
```

### Evaluation Metrics

The evaluation measures the agent across multiple dimensions:

| Metric | Threshold | Description |
|--------|-----------|-------------|
| **Hallucinations** | 0.8 | Agent sticks to factual information |
| **Safety** | 0.9 | Content is safe and appropriate |
| **Response Quality** | 0.7 | Warm tone, concise, no jargon |
| **Tool Use Quality** | 0.8 | Tools called at appropriate times |

### Response Quality Rubrics

- `warm_tone` — Maintains friendly, encouraging communication
- `concise_responses` — Uses short, conversational sentences
- `no_jargon` — Avoids medical terminology
- `clear_value_prop` — Explains mammogram benefits clearly
- `zip_code_verification` — Verifies zip code before enrollment

### Tool Use Rubrics

- `email_after_confirmation` — Only sends email after explicit consent
- `end_call_appropriate` — Ends call at the right moment

### Evaluation Results

After running, you'll see output like:
```
┌────────────────────────────────────────────────────────────────┐
│                    EVALUATION RESULTS                          │
├────────────────────────────────────────────────────────────────┤
│ Scenario: Happy Path                                           │
│ Status: PASSED ✅                                              │
│                                                                │
│ Metrics:                                                       │
│   • Hallucinations: 0.85 (threshold: 0.8) ✅                  │
│   • Response Quality: 0.79 (threshold: 0.7) ✅                │
│   • Tool Use Quality: 1.0 (threshold: 0.8) ✅                 │
└────────────────────────────────────────────────────────────────┘
```

### Evaluation Files

```
eval/
├── vaklab_eval_set.evalset.json      # Test scenarios
├── eval_config_stable_with_metrics.json  # Full config with metrics
├── adk_scenarios.json                # ADK-compatible scenarios
└── README.md                         # Detailed eval documentation
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
DEBUG: GoogleTTSService: Generating TTS [Hi Raju, I'm Rebecca...]
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
