# Real-Time Transcript UI

This feature displays live transcripts of outbound calls in a web-based dashboard.

## Features

- **Real-time transcript updates** via WebSocket
- **Live call status** (active, ended)
- **Speaker identification** (AI vs Customer)
- **Call metadata** display (member name, phone, campaign)
- **Call duration timer**
- **Multiple simultaneous calls** support

## Usage

### 1. Start the Server

```bash
python main.py
```

The server will start on `http://localhost:8000`

### 2. Open the Transcript Dashboard

Navigate to:
```
http://localhost:8000/static/index.html
```

### 3. Make an Outbound Call

```bash
curl -X POST http://localhost:8000/twilio/outbound-call
```

### 4. Watch Live Transcripts

The UI will automatically:
- Show the new call in the sidebar
- Display real-time conversation as it happens
- Update call status and duration
- Show system events (email sent, call ended, etc.)

## Architecture

### Backend Components

1. **`utils/transcript_manager.py`**
   - Manages active call transcripts
   - Broadcasts events to connected UI clients
   - Stores conversation history

2. **`routers/transcript_ui.py`**
   - WebSocket endpoint `/ui/transcripts` for UI clients
   - REST endpoint `/ui/active-calls` for active calls list

3. **`routers/pipe_bot.py`**
   - `TranscriptCaptureProcessor` hooks into Pipecat pipeline
   - Captures STT (Speech-to-Text) frames
   - Captures LLM response frames
   - Emits transcript events in real-time

### Frontend Components

1. **`frontend/index.html`** - Main dashboard UI
2. **`frontend/app.js`** - WebSocket client and UI logic
3. **`frontend/styles.css`** - Modern, responsive styling

## WebSocket Events

The UI WebSocket receives these event types:

- `init` - Initial state with active calls
- `call_started` - New call initiated
- `transcript_message` - New message in conversation
- `call_ended` - Call terminated
- `call_status_update` - Status change

## Message Types

Transcript messages have these types:

- `speech` - Regular conversation (AI or Customer)
- `tool_call` - System action (e.g., email sent)
- `system` - System notification (e.g., call ended)

## Deployment Notes

For production deployment:

1. Use HTTPS/WSS protocol
2. Configure proper CORS settings
3. Consider Redis for transcript storage across multiple server instances
4. Add authentication for the transcript UI
5. Store transcripts in database for historical review
