# VakLab Test Execution Checklist

## Pre-Flight Setup (One-Time)

### 1. Install pipecat-ai
```bash
pip install "pipecat-ai[google,silero]"
```

### 2. Update .env with Real Credentials

```bash
# Edit the file
nano .env

# Update these values:
TWILIO_SID=ACxxxxxxxxxxxxxxxxxx
TWILIO_AUTH=your_auth_token_here
TWILIO_NUMBER=+19135960926
GOOGLE_API_KEY=AIzaSyAaUAr5_N_6ATPyyljmz1gy8Kr-PX3guDg

# SMTP (optional - only needed for HEDIS email)
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
```

### 3. Start ngrok (Keep Running)
```bash
# Terminal 1
ngrok http 8000

# Copy the HTTPS URL, example:
# https://abc123.ngrok-free.app
```

### 4. Update DOMAIN in .env
```bash
DOMAIN=https://abc123.ngrok-free.app
```

---

## Running a Test (Every Time)

### Terminal 1: ngrok (Already Running)
```bash
ngrok http 8000
# Keep this running
```

### Terminal 2: Start Server
```bash
cd /Users/peterscheuermann/Documents/VakLab

# Set Google credentials
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/cool-furnace-483603-b2-fdd4814415cb.json"

# Start server (or use helper script)
./start.sh

# OR manually:
# uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Wait for:
```
INFO:     Application startup complete.
```

### Terminal 3: Run Test
```bash
cd /Users/peterscheuermann/Documents/VakLab

# Option A: Automated test workflow
python test_complete.py

# Option B: Manual trigger
curl -X POST http://localhost:8000/twilio/outbound-call
```

### What to Expect

1. **API Response:**
   ```json
   {
     "status": "queued",
     "call_sid": "CAxxxxxx",
     "member_id": "1001",
     "campaign": "Metna Breast Screening Partner Program"
   }
   ```

2. **Server Logs (Terminal 2):**
   ```
   📞 /voice-entry called with phone=9135960926
   [EVENT] Pipecat bot connected for Raju
   [GREETING] Triggered LLM to generate greeting
   [TOOL] send_enrollment_email called
   ✓ Enrollment email sent
   [TOOL] end_call triggered
   ```

3. **Phone Rings:**
   - Answer the call
   - Hear: "This call may be recorded for quality and training purposes."
   - Agent greets you by name
   - Have a conversation following the campaign flow

---

## After the Call

### Download Recording
```bash
# Wait 30-60 seconds for recording to be available
python download_recording.py

# Check for MP3 file
ls -lh recording_*.mp3
```

### Review Server Logs
- Scroll through Terminal 2
- Look for errors or warnings
- Verify tool executions

### Check Database
```bash
docker exec -it outbound_agent_db psql -U user -d outbound_agent_db

# Check call status
SELECT * FROM campaign_target_member_call_list WHERE member_id='1001';

# Exit
\q
```

### Twilio Console
- Go to: https://console.twilio.com/monitor/logs/calls
- Find your call by SID
- Review call logs and recording

---

## Testing Different Scenarios

### Reset for Another Test
```bash
# Reset call status in database
docker exec -it outbound_agent_db psql -U user -d outbound_agent_db -c \
  "UPDATE campaign_target_member_call_list SET call_status='Not Called' WHERE member_id='1001';"
```

### Test HEDIS Campaign (Default)
```sql
UPDATE campaign_target_member_call_list 
SET campaign_name='Metna Breast Screening Partner Program', 
    call_status='Not Called'
WHERE member_id='1001';
```

**Expected Flow:**
1. Greeting by name
2. Zip code verification
3. Mammogram explanation
4. Enrollment offer
5. Email sent (check inbox)
6. Goodbye

### Test Appointment Campaign
```bash
docker exec -it outbound_agent_db psql -U user -d outbound_agent_db -c \
  "UPDATE campaign_target_member_call_list 
   SET campaign_name='appointment_backfill', call_status='Not Called'
   WHERE member_id='1001';"
```

**Expected Flow:**
1. Clinic introduction
2. Offer earlier appointment slot
3. Accept/decline handling
4. If accepted: reschedule + SMS confirmation
5. Goodbye

---

## Conversation Examples

### HEDIS - Happy Path
```
Agent: "Hi Raju, I'm Metna..."
You: "Yes, I have a few minutes"
Agent: "Could you tell me your zip code?"
You: "75087"
Agent: "...Would you like to enroll?"
You: "Yes, please"
Agent: "I'll send details to your email. Watch for that email."
You: "Thanks"
Agent: "Have a great day!"
```

### HEDIS - With Objection
```
Agent: "...Would you like to enroll?"
You: "Is there a catch? What does it cost?"
Agent: "No catch! For most members this is fully covered..."
You: "Ok, I'll enroll"
Agent: "Great! I'll send the email now..."
```

### Appointment - Happy Path
```
Agent: "Hi Mark, calling from Northview Family Medicine..."
You: "Sure, what's up?"
Agent: "We have a cancellation for Feb 1st at 2:30 PM..."
You: "That works better for me"
Agent: "Perfect! Moving you into that spot..."
You: "Thanks"
Agent: "You'll get a text confirmation. Have a great day!"
```

---

## Troubleshooting

### Call Doesn't Connect
- [ ] Check ngrok is running
- [ ] Verify DOMAIN in .env matches ngrok URL
- [ ] Restart server after .env changes
- [ ] Check ngrok web UI: http://127.0.0.1:4040

### Agent Doesn't Speak
- [ ] Check server logs for errors
- [ ] Verify Google credentials are set
- [ ] Check GOOGLE_API_KEY in .env
- [ ] Ensure pipecat-ai is installed with [google,silero]

### No Recording Available
- [ ] Wait 60 seconds after call ends
- [ ] Check Twilio console for recording
- [ ] Verify TWILIO_SID and TWILIO_AUTH are correct
- [ ] Recording may take time to process

### Tool Doesn't Execute (Email/SMS)
- [ ] Check server logs for error messages
- [ ] For email: verify SMTP credentials
- [ ] For SMS: verify Twilio credentials
- [ ] Check database connection

### Database Errors
- [ ] Ensure Docker container is running: `docker ps`
- [ ] Restart if needed: `docker compose restart`
- [ ] Check logs: `docker logs outbound_agent_db`

---

## Quick Commands Reference

```bash
# Start everything
./start.sh

# Check health
curl http://localhost:8000/health

# Trigger call
curl -X POST http://localhost:8000/twilio/outbound-call

# Download recording
python download_recording.py

# Reset database
docker exec -it outbound_agent_db psql -U user -d outbound_agent_db -c \
  "UPDATE campaign_target_member_call_list SET call_status='Not Called';"

# View database
docker exec -it outbound_agent_db psql -U user -d outbound_agent_db -c \
  "SELECT * FROM campaign_target_member_call_list;"

# Stop server
pkill -f "uvicorn main:app"

# Stop ngrok
pkill ngrok

# Stop database
docker compose down
```

---

## Success Criteria

✅ **Call connects** - Phone rings  
✅ **Agent speaks first** - Greeting with correct name  
✅ **Agent responds** - Handles your responses naturally  
✅ **Tools execute** - Email sent / Appointment rescheduled  
✅ **Call ends gracefully** - Agent says goodbye  
✅ **Recording available** - Can download MP3  
✅ **Logs are clean** - No errors in server terminal  

---

## Next Steps After Successful Test

1. **Review the gap analysis documents** in `instruct/gap_analysis/research/`
2. **Test different conversation scenarios** (objections, busy, etc.)
3. **Try the automated eval framework** with `eval/eval_runner.py`
4. **Start implementing Phase 1 fixes** from `03_remediation_roadmap.md`

---

## Notes

- Recording includes both you and the agent (dual channel)
- First call may take longer as AI models initialize
- Each test call costs Twilio credits (~$0.01-0.05)
- Recordings auto-delete from Twilio after 30-90 days (configurable)
- For production, implement proper consent and retention policies
