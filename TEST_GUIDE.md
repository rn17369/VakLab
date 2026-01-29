# Testing Guide for Outbound Call System

This guide covers testing for both **HEDIS** and **Appointment Backfill** campaigns.

## Prerequisites

1. **Database Setup**: PostgreSQL running with all schema files loaded:
   - `01_init.sql` - Core schema + HEDIS member data
   - `02_eval_schema.sql` - Evaluation tracking
   - `03_clinic_scheduler.sql` - Clinic/appointment data
2. **Environment Variables**: Copy `.env.example` to `.env` and fill in values
3. **Ngrok**: Make sure ngrok is running and DOMAIN in `.env` is updated
4. **Twilio Account**: Verify TWILIO_SID, TWILIO_AUTH, and TWILIO_NUMBER are correct
5. **Google API Key**: Ensure GOOGLE_API_KEY is set (for ADK evals)

## Step 1: Start the Server

```bash
# From the project root directory
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Step 2: Run ADK Evaluations (Recommended)

ADK evaluations test the agent conversation flow without making real calls.

### HEDIS Campaign Evaluation
```bash
# Set environment and run
export GOOGLE_API_KEY=$(grep "^GOOGLE_API_KEY=" .env | cut -d '=' -f2)
export GOOGLE_GENAI_USE_VERTEXAI=0

adk eval agents/outbound_agent metna_eval_set \
    --config_file_path eval/eval_config_stable_with_metrics.json \
    --print_detailed_results
```

**Expected Results:**
- Overall Score: ~0.81
- Hallucinations: ~0.81 (threshold: 0.8)
- Tool Use: ~0.94 (threshold: 0.8)
- Response Quality: ~0.68 (threshold: 0.7)

### Appointment Campaign Evaluation
```bash
# Use the helper script (handles env vars)
./run_appointment_eval.sh

# Or manually:
adk eval agents/outbound_agent appointment_eval_set \
    --config_file_path eval/eval_config_appointment.json \
    --print_detailed_results
```

**Expected Results:**
- Overall: PASSED
- Hallucinations: ~1.0
- Tool Use: ~0.92
- Response Quality: ~0.75

## Step 3: Run Integration Test Script

In a new terminal:

```bash
# Make the test script executable
chmod +x test_outbound.py

# Run the test
python test_outbound.py
```

## Step 4: Manual Testing with curl

### Test Health Endpoint
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```

### Test Outbound Call
```bash
curl -X POST http://localhost:8000/twilio/outbound-call
```

Expected responses:

**Success:**
```json
{
  "status": "queued",
  "call_sid": "CA1234567890abcdef",
  "member_id": "12345",
  "campaign": "Metna Better Care Rewards"
}
```

**No numbers to call:**
```json
{
  "status": "info",
  "message": "No numbers to call"
}
```

**Error:**
```json
{
  "error": "Error message here"
}
```

## Step 5: Monitor Logs

Watch the server logs to see:
- Database queries
- Twilio call initiation
- WebSocket connections
- Agent interactions
- Speech-to-text processing
- Text-to-speech generation

## Step 6: Check Database

After a call is initiated, check the database:

### HEDIS Campaign Tables
```sql
-- Check call status
SELECT member_id, phone_number, campaign_name, call_status 
FROM campaign_target_member_call_list 
ORDER BY updated_at DESC 
LIMIT 10;

-- Check call details
SELECT * FROM campaign_call_details 
ORDER BY call_date DESC 
LIMIT 5;
```

### Appointment Campaign Tables
```sql
-- Check appointments
SELECT a.id, p.first_name, p.last_name, pr.name as provider, 
       a.scheduled_date, a.status
FROM appointments a
JOIN patients p ON a.patient_id = p.id
JOIN providers pr ON a.provider_id = pr.id
ORDER BY a.scheduled_date DESC;

-- Check backfill queue
SELECT * FROM appointment_backfill_queue 
WHERE status = 'pending';

-- Check eval runs
SELECT run_id, campaign_type, status, overall_score 
FROM eval_runs 
ORDER BY created_at DESC LIMIT 5;
```

## Troubleshooting

### Server won't start
- Check if port 8000 is already in use: `lsof -i :8000`
- Verify all dependencies are installed: `pip install -r requirements.txt`

### "No numbers to call" message
- Check database has records with `call_status = 'Not Called'`
- Run SQL: `INSERT INTO campaign_target_member_call_list ...` (see outbound_campiagn_agent.sql)

### Twilio errors
- Verify TWILIO_SID and TWILIO_AUTH are correct
- Check TWILIO_NUMBER is a valid Twilio phone number
- Ensure ngrok is running and DOMAIN is updated

### Database connection errors
- Check PostgreSQL is running: `pg_isready`
- Verify DB credentials in `.env`
- Test connection: `psql -h localhost -U user -d outbound_agent_db`

### Google Cloud credentials error
- Verify `cool-furnace-483603-b2-fdd4814415cb.json` exists
- Check file permissions
- Ensure Google Cloud APIs are enabled

## Expected Call Flow

1. **Call Initiated**: System picks a member/patient from database
2. **Twilio Connects**: Call is placed to phone
3. **WebSocket Opens**: Twilio establishes media stream
4. **Orchestrator Routes**: `OutboundOrchestrator` detects campaign type and instantiates correct agent
5. **Agent Greets**: 
   - HEDIS: "Hi [Name], I'm Metna..."
   - Appointment: "Hi, calling from the clinic..."
6. **Conversation**: Agent follows campaign-specific flow
7. **Tools Execute**: 
   - HEDIS: `send_enrollment_email`, `end_call`
   - Appointment: `reschedule_appointment`, `send_confirmation_sms`, `end_call`
8. **Call Ends**: Agent calls `end_call()` and updates database

## Key Endpoints

- `POST /twilio/outbound-call` - Initiate an outbound call
- `POST /twilio/voice-entry` - TwiML endpoint for call connection
- `WebSocket /twilio/stream` - Media stream handler
- `POST /twilio/callback` - Twilio status callbacks
- `GET /health` - Health check

## Testing Checklist

### Infrastructure
- [ ] Server starts without errors
- [ ] Health endpoint responds
- [ ] Database connection works (all 3 schema files loaded)

### ADK Evaluations
- [ ] HEDIS eval runs: `adk eval agents/outbound_agent metna_eval_set`
- [ ] Appointment eval runs: `./run_appointment_eval.sh`
- [ ] Correct agent is used (check logs for `MetnaAgent` vs `SchedulingAssistant`)
- [ ] Metrics pass thresholds

### Live Call Testing (HEDIS)
- [ ] Outbound call endpoint returns success
- [ ] Twilio call is initiated
- [ ] WebSocket connection established
- [ ] STT recognizes speech
- [ ] LLM generates responses (Metna agent)
- [ ] TTS converts text to audio
- [ ] `send_enrollment_email` executes successfully
- [ ] `end_call` terminates properly

### Live Call Testing (Appointment)
- [ ] Call with `campaign=appointment_backfill` routes correctly
- [ ] SchedulingAssistant agent responds
- [ ] `reschedule_appointment` updates database
- [ ] `send_confirmation_sms` sends SMS via Twilio
- [ ] Appointment status changes in database
