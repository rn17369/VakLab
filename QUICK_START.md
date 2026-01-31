# VakLab Quick Start Guide - Run & Test with Recording

> **Goal:** Get the system running, make a test call, and record the entire conversation

---

## Pre-Flight Checklist

### ✅ What's Already Set Up
- [x] PostgreSQL database is running (port 5432)
- [x] Python 3.12 installed
- [x] Core dependencies installed (FastAPI, Google ADK, Twilio)
- [x] ngrok installed
- [x] Google credentials file exists

### ⚠️ What Needs Configuration
- [ ] .env file with real credentials
- [ ] ngrok tunnel started
- [ ] Pipecat-AI with Google extras installed
- [ ] Server running

---

## Step 1: Install Missing Dependencies

```bash
cd /Users/peterscheuermann/Documents/VakLab

# Install pipecat with Google and Silero support
pip install "pipecat-ai[google,silero]"

# Verify installation
pip list | grep pipecat
```

---

## Step 2: Configure Environment Variables

Edit `.env` file with real values:

```bash
nano .env
```

### Required Values to Update:

```bash
# Twilio (get from https://console.twilio.com/)
TWILIO_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH=your_actual_auth_token
TWILIO_NUMBER=+19135960926  # Your Twilio phone number

# SMTP (for HEDIS email tool - optional for appointment campaign)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password

# Domain - will update this after starting ngrok
DOMAIN=https://placeholder.ngrok.io
```

---

## Step 3: Fix Hardcoded Google Credentials Path

**Current Issue:** Credentials path is hardcoded in `pipe_bot.py`

**Quick Fix:**

```bash
# Option A: Create symlink at expected location
mkdir -p /Users/rn/Documents/gcp_hackthon
ln -s $(pwd)/cool-furnace-483603-b2-fdd4814415cb.json /Users/rn/Documents/gcp_hackthon/cool-furnace-483603-b2-fdd4814415cb.json

# Option B: Set environment variable (better)
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/cool-furnace-483603-b2-fdd4814415cb.json"
```

---

## Step 4: Start ngrok Tunnel

In a **new terminal window**:

```bash
ngrok http 8000
```

You'll see output like:
```
Forwarding  https://abc123def456.ngrok-free.app -> http://localhost:8000
```

**Copy the HTTPS URL** (e.g., `https://abc123def456.ngrok-free.app`)

### Update .env with ngrok URL:

```bash
DOMAIN=https://abc123def456.ngrok-free.app
```

---

## Step 5: Enable Call Recording (Twilio)

**Edit:** `routers/outbound_twillio.py`

Find the `voice_entry` function and add recording to TwiML:

```python
# Around line 150, after creating the VoiceResponse
response = VoiceResponse()

# ADD THIS LINE to enable recording
response.say("This call may be recorded for quality assurance.")
```

Then in the Stream parameters, add:
```python
# Around line 165
stream.parameter(name="record", value="true")
```

**Better approach:** Let me create a patch for you.

---

## Step 6: Start the FastAPI Server

In your main terminal:

```bash
cd /Users/peterscheuermann/Documents/VakLab

# Set credentials environment variable
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/cool-furnace-483603-b2-fdd4814415cb.json"

# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using StatReload
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## Step 7: Test the Setup

In a **third terminal window**:

```bash
cd /Users/peterscheuermann/Documents/VakLab

# Test 1: Health check
curl http://localhost:8000/health

# Test 2: Trigger an outbound call
curl -X POST http://localhost:8000/twilio/outbound-call
```

Expected response:
```json
{
  "status": "queued",
  "call_sid": "CAxxxxxxxxxxxx",
  "member_id": "1001",
  "campaign": "Metna Breast Screening Partner Program"
}
```

---

## Step 8: Monitor the Call

### Watch Server Logs
In your server terminal, you'll see:
```
📞 /voice-entry called with phone=9135960926, member_id=1001, campaign=Metna...
[EVENT] Pipecat bot connected for Raju
[GREETING] Triggered LLM to generate greeting
[TOOL] send_enrollment_email called for Raju at nekadiraju@gmail.com
```

### Check Twilio Console
1. Go to https://console.twilio.com/monitor/logs/calls
2. Find your call SID
3. Click to see call details and recording

---

## Step 9: Retrieve Call Recording

### Option A: Via Twilio Console
1. Go to https://console.twilio.com/monitor/logs/calls
2. Click on your call
3. Click "Download" next to the recording

### Option B: Via API (Python Script)

Create `download_recording.py`:

```python
#!/usr/bin/env python3
import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

client = Client(
    os.getenv("TWILIO_SID"),
    os.getenv("TWILIO_AUTH")
)

# Get most recent call
calls = client.calls.list(limit=1)
if calls:
    call = calls[0]
    print(f"Call SID: {call.sid}")
    print(f"Status: {call.status}")
    print(f"Duration: {call.duration} seconds")
    
    # Get recordings for this call
    recordings = client.recordings.list(call_sid=call.sid)
    for recording in recordings:
        print(f"\nRecording SID: {recording.sid}")
        print(f"Duration: {recording.duration} seconds")
        
        # Download URL
        url = f"https://api.twilio.com/2010-04-01/Accounts/{os.getenv('TWILIO_SID')}/Recordings/{recording.sid}.mp3"
        print(f"Download: {url}")
        
        # Or download directly
        import requests
        auth = (os.getenv("TWILIO_SID"), os.getenv("TWILIO_AUTH"))
        response = requests.get(url, auth=auth)
        
        with open(f"call_{call.sid}.mp3", "wb") as f:
            f.write(response.content)
        print(f"✓ Saved to call_{call.sid}.mp3")
```

Run it:
```bash
python download_recording.py
```

---

## Step 10: Review the Call Data

### Database Inspection

```bash
# Connect to PostgreSQL
docker exec -it outbound_agent_db psql -U user -d outbound_agent_db

# Check call was logged
SELECT * FROM campaign_target_member_call_list;

# Exit
\q
```

### Server Logs
- Check `uvicorn` terminal for full conversation flow
- Look for tool invocations (`[TOOL] send_enrollment_email called`)
- Verify call ended properly

---

## Troubleshooting

### Issue: "Connection refused" when triggering call
**Fix:** Ensure ngrok URL is updated in `.env` and server was restarted

### Issue: "Google credentials not found"
**Fix:** Set environment variable before starting server:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/cool-furnace-483603-b2-fdd4814415cb.json"
```

### Issue: No audio on call
**Fix:** Check that pipecat-ai was installed with Google extras:
```bash
pip install "pipecat-ai[google,silero]" --force-reinstall
```

### Issue: Call connects but agent doesn't speak
**Fix:** Check server logs for errors. Likely causes:
- Google API key invalid
- Google credentials file not found
- TTS service initialization failed

### Issue: Twilio webhook not receiving call
**Fix:** 
1. Verify ngrok is running and URL is correct
2. Check ngrok web UI at http://127.0.0.1:4040 to see incoming requests
3. Ensure `.env` has correct DOMAIN value

---

## Testing Different Campaigns

### HEDIS/Metna Campaign (Default)
```sql
-- Ensure this record exists
INSERT INTO campaign_target_member_call_list (member_id, phone_number, campaign_name, call_status)
VALUES ('1001', '9135960926', 'Metna Better Care Rewards', 'Not Called')
ON CONFLICT (member_id) DO UPDATE SET call_status = 'Not Called';
```

### Appointment Backfill Campaign
```sql
-- Add an appointment campaign record
INSERT INTO campaign_target_member_call_list (member_id, phone_number, campaign_name, call_status)
VALUES ('2001', '9135960926', 'appointment_backfill', 'Not Called')
ON CONFLICT (member_id) DO UPDATE SET call_status = 'Not Called';
```

Then trigger call as usual.

---

## Expected Call Flow for HEDIS Campaign

1. **Agent:** "Hi Raju, I'm Metna. I'm calling from the Metna Breast Screening Partner Program to discuss your breast health. Do you have a few minutes to talk about a quick health check?"

2. **You:** "Yes"

3. **Agent:** "Wonderful. First, to find the best screening centers near you, could you please tell me your current zip code?"

4. **You:** "75087"

5. **Agent:** "Thank you. I see some great centers nearby. A mammogram is just a 15-minute breast X-ray..."

6. **You:** "Yes, please enroll me"

7. **Agent:** "That's wonderful! I'm enrolling you now. I'll send the full details to your email..."

8. **[Tool Execution]:** Email sent

9. **Agent:** "Excellent. You're all set! Watch for that email. Is there anything else I can help you with?"

10. **You:** "No, that's all"

11. **Agent:** "Thank you for your time. Have a great day!"

12. **[Call ends]**

---

## Next Steps

After successful test:
1. Review recordings in Twilio console
2. Check email was received (HEDIS campaign)
3. Verify database was updated
4. Test with different scenarios (objections, busy, etc.)
5. Try appointment campaign

---

## Recording Best Practices

1. **Always announce recording:** "This call may be recorded..."
2. **Store recordings securely:** Don't commit to git
3. **Comply with state laws:** Some states require two-party consent
4. **Set retention policy:** Auto-delete after X days

For production, implement:
- Encryption at rest for recordings
- Access controls
- Audit logging of who accessed recordings
