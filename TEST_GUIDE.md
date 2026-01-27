# Testing Guide for Outbound Call System

## Prerequisites

1. **Database Setup**: Make sure your PostgreSQL database is running and has the required tables
2. **Environment Variables**: Check that your `.env` file has all required values
3. **Ngrok**: Make sure ngrok is running and DOMAIN in `.env` is updated
4. **Twilio Account**: Verify TWILIO_SID, TWILIO_AUTH, and TWILIO_NUMBER are correct

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

## Step 2: Run the Test Script

In a new terminal:

```bash
# Make the test script executable
chmod +x test_outbound.py

# Run the test
python test_outbound.py
```

## Step 3: Manual Testing with curl

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

## Step 4: Monitor Logs

Watch the server logs to see:
- Database queries
- Twilio call initiation
- WebSocket connections
- Agent interactions
- Speech-to-text processing
- Text-to-speech generation

## Step 5: Check Database

After a call is initiated, check the database:

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

1. **Call Initiated**: System picks a member from database
2. **Twilio Connects**: Call is placed to member's phone
3. **WebSocket Opens**: Twilio establishes media stream
4. **Agent Greets**: "Hi [Name], I'm Metna..."
5. **Conversation**: Agent follows the state machine (Hook → Value Prop → Enrollment)
6. **Tools Execute**: send_enrollment_email, update database, etc.
7. **Call Ends**: Agent calls end_call() and updates database

## Key Endpoints

- `POST /twilio/outbound-call` - Initiate an outbound call
- `POST /twilio/voice-entry` - TwiML endpoint for call connection
- `WebSocket /twilio/stream` - Media stream handler
- `POST /twilio/callback` - Twilio status callbacks
- `GET /health` - Health check

## Testing Checklist

- [ ] Server starts without errors
- [ ] Health endpoint responds
- [ ] Database connection works
- [ ] Outbound call endpoint returns success
- [ ] Twilio call is initiated
- [ ] WebSocket connection established
- [ ] STT recognizes speech
- [ ] LLM generates responses
- [ ] TTS converts text to audio
- [ ] Tools execute successfully
- [ ] Database updates correctly
- [ ] Call ends gracefully
