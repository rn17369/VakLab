import os
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Form, Request, Response, WebSocket
from fastapi.params import Depends
from fastapi.responses import HTMLResponse
from twilio.rest import Client
from twilio.twiml.voice_response import Connect, Stream, VoiceResponse

#from routers.manual_bot import run_manual_bot
from routers.pipe_bot import run_pipe_bot

from entities.twilio import (
    TwilioStreamCallbackPayload,
    TwilioVoiceWebhookPayload,
)
from utils.env import is_local
from utils.db import get_db_connection
from utils.security import validate_twilio
import logging

# Setup logger
logger = logging.getLogger(__name__)


twilio_path = "/twilio"
callback_path = "/callback"
stream_path = "/stream"
router = APIRouter(prefix=twilio_path, tags=["Twilio Webhooks"])

# Twilio client setup - load lazily to ensure env vars are set
def get_twilio_client():
    """Get Twilio client (lazy load to ensure env vars are set)"""
    sid = os.getenv("TWILIO_SID")
    auth = os.getenv("TWILIO_AUTH")
    if not sid or not auth:
        raise ValueError("TWILIO_SID or TWILIO_AUTH not set")
    return Client(sid, auth)

TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
DOMAIN = os.getenv("DOMAIN")


@router.post("/connect", dependencies=[Depends(validate_twilio)])
def create_call(req: Request, payload: Annotated[TwilioVoiceWebhookPayload, Form()]):
    """Generate TwiML to connect a call to a Twilio Media Stream"""

    host = req.url.hostname
    ws_protocol = "ws" if is_local else "wss"
    http_protocol = "http" if is_local else "https"
    ws_url = f"{ws_protocol}://{host}{twilio_path}{stream_path}"
    callback_url = f"{http_protocol}://{host}{twilio_path}{callback_path}"

    stream = Stream(url=ws_url, statusCallback=callback_url)
    stream.parameter(name="from_phone", value=payload.From)
    stream.parameter(name="to_phone", value=payload.To)
    connect = Connect()
    connect.append(stream)
    response = VoiceResponse()
    response.append(connect)

    logger.info(response)

    return HTMLResponse(content=str(response), media_type="application/xml")


@router.post(callback_path, status_code=204)
def twilio_callback(payload: Annotated[TwilioStreamCallbackPayload, Form()]):
    """Handle Twilio status callbacks"""

    logger.info(f"✓ Callback received: {payload.CallSid}")

    return Response(status_code=204)


@router.post("/outbound-call")
async def make_call():
    """Make an outbound call by picking the next target from the database"""
    # Use DOMAIN from env, or default to localhost for local testing
    domain = DOMAIN or "http://localhost:8000"
    clean_domain = domain.replace("https://", "").replace("http://", "")
    logger.info(f"🌐 Using domain: {domain} (cleaned: {clean_domain})")
    
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}

    try:
        cur = conn.cursor()
        
        # 1. Fetch next 'Not Called' member (Queue logic - no status update for testing)
        cur.execute("""
            SELECT member_id, phone_number, campaign_name 
            FROM campaign_target_member_call_list 
            WHERE call_status = 'Not Called' 
            LIMIT 1
        """)
        row = cur.fetchone()
        
        if not row:
            return {"status": "info", "message": "No numbers to call"}
        
        member_id, phone_number, campaign_name = row
        phone_number = phone_number.strip()

        # 3. Initiate Call (no status updates - record stays 'Not Called' for testing)
        try:
            twilio_client = get_twilio_client()
            call = twilio_client.calls.create(
                to=phone_number,
                from_=TWILIO_NUMBER,
                url=f"https://{clean_domain}{twilio_path}/voice-entry?phone={phone_number}&member_id={quote(str(member_id))}&campaign={quote(campaign_name)}"
            )
            return {
                "status": "queued", 
                "call_sid": call.sid, 
                "member_id": member_id, 
                "campaign": campaign_name
            }
        except Exception as twilio_ex:
            logger.error(f"Twilio Call Failed: {twilio_ex}")
            return {"error": f"Twilio start failed: {str(twilio_ex)}"}

    except Exception as ex:
        if conn:
            conn.rollback()
        logger.exception(f"DB Error in make_call: {ex}")
        return {"error": str(ex)}
    finally:
        if conn:
            conn.close()


@router.post("/voice-entry")
def voice_entry(req: Request, phone: str = None, member_id: str = None, campaign: str = None):
    """Return TwiML that connects the call to a Media Stream"""
    logger.info("=" * 80)
    logger.info(f"📞 /voice-entry called with phone={phone}, member_id={member_id}, campaign={campaign}")
    
    try:
        host = req.headers.get("x-forwarded-host", req.url.hostname)
        logger.info(f"   Host: {host}")
        
        ws_protocol = "ws" if is_local else "wss"
        http_protocol = "http" if is_local else "https"
        ws_url = f"{ws_protocol}://{host}{twilio_path}{stream_path}"
        callback_url = f"{http_protocol}://{host}{twilio_path}{callback_path}"
        
        logger.info(f"   WebSocket URL: {ws_url}")
        logger.info(f"   Callback URL: {callback_url}")

        stream = Stream(url=ws_url, statusCallback=callback_url)
        stream.parameter(name="from_phone", value=phone or "")
        stream.parameter(name="to_phone", value=TWILIO_NUMBER)
        stream.parameter(name="member_id", value=member_id or "")
        stream.parameter(name="campaign", value=campaign or "")
        connect = Connect()
        connect.append(stream)
        response = VoiceResponse()
        response.append(connect)

        twiml_response = str(response)
        logger.info(f"✓ TwiML generated successfully:")
        logger.info(f"{twiml_response}")

        return HTMLResponse(content=twiml_response, media_type="application/xml")
    except Exception as ex:
        logger.error(f"✗ /voice-entry FAILED: {ex}", exc_info=True)
        raise


# TODO: Figure out how to validate Twilio signature in a WebSocket
# https://www.twilio.com/docs/usage/webhooks/webhooks-security
# Headers({'host': 'amazing-sincere-grouse.ngrok-free.app', 'user-agent': 'Twilio.TmeWs/1.0', 'connection': 'Upgrade', 'sec-websocket-key': '', 'sec-websocket-version': '13', 'upgrade': 'websocket', 'x-forwarded-for': '98.84.178.199', 'x-forwarded-host': 'amazing-sincere-grouse.ngrok-free.app', 'x-forwarded-proto': 'https', 'x-twilio-signature': '', 'accept-encoding': 'gzip'})


@router.websocket(stream_path)
async def twilio_websocket(ws: WebSocket):
    """Handle Twilio Media Stream WebSocket connection"""

    logger.info("=" * 80)
    logger.info("🔵 STEP 1: WebSocket connection received from Twilio")
    
    await ws.accept()
    logger.info("✓ STEP 2: WebSocket accepted")
    
    try:
        _ = await ws.receive_json()  # connected event (not used)
        logger.info("✓ STEP 3: Connected event received")
    except Exception as ex:
        logger.error(f"✗ STEP 3 FAILED: Could not receive connected event: {ex}", exc_info=True)
        await ws.close()
        return

    try:
        start_event = await ws.receive_json()
        logger.info(f"✓ STEP 4: Start event received")
    except Exception as ex:
        logger.error(f"✗ STEP 4 FAILED: Could not receive start event: {ex}", exc_info=True)
        await ws.close()
        return

    if start_event.get("event") != "start":
        logger.error(f"✗ STEP 5 FAILED: Expected 'start' event, got: {start_event.get('event')}")
        await ws.close()
        return
    
    logger.info(f"✓ STEP 5: Start event validated")

    try:
        call_sid = start_event["start"]["callSid"]
        from_phone = start_event["start"]["customParameters"].get("from_phone", "unknown")
        to_phone = start_event["start"]["customParameters"].get("to_phone", "unknown")
        member_id = start_event["start"]["customParameters"].get("member_id")
        campaign = start_event["start"]["customParameters"].get("campaign")
        stream_sid = start_event["streamSid"]
        
        logger.info(f"✓ STEP 6: Extracted call info - Call SID: {call_sid}, Phone: {from_phone}, Member: {member_id}, Campaign: {campaign}")
    except Exception as ex:
        logger.error(f"✗ STEP 6 FAILED: Could not extract call info: {ex}", exc_info=True)
        await ws.close()
        return

    # Use pipe_bot with Pipecat framework
    try:
        logger.info(f"✓ STEP 7: Starting Pipecat bot for {from_phone}...")
        await run_pipe_bot(
            websocket=ws,
            stream_sid=stream_sid,
            call_sid=call_sid,
            to_number=from_phone,
            from_number=to_phone,
            member_id=member_id,
            campaign=campaign
        )
        logger.info(f"✓ STEP 8: Pipecat bot session completed")
    except Exception as ex:
        logger.error(f"✗ STEP 7-8 FAILED: Pipecat bot error: {ex}", exc_info=True)
    finally:
        try:
            await ws.close()
            logger.info("✓ WebSocket closed")
        except Exception as ex:
            logger.warning(f"⚠ Error while closing WebSocket: {ex}")

    # https://www.twilio.com/docs/voice/media-streams/websocket-messages
    # {'event': 'connected', 'protocol': 'Call', 'version': '1.0.0'}
    # {'event': 'start', 'sequenceNumber': '1', 'start': {'accountSid': '', 'streamSid': '', 'callSid': '', 'tracks': ['inbound'], 'mediaFormat': {'encoding': 'audio/x-mulaw', 'sampleRate': 8000, 'channels': 1}, 'customParameters': {'caller': ''}}, 'streamSid': ''}
    # {'event': 'media', 'sequenceNumber': '2', 'media': {'track': 'inbound', 'chunk': '1', 'timestamp': '57', 'payload': '+33+/3t7/f3/fvv7fX3+/f5+/vv2fnv8ePt9ff59fn97/nr//3v9fH14+Hj+fv3++3x+/3j+fn35/f58fX3/e/15ff7+ff78+318/X99/P39/nx9f319+v3+fvp9///9/f5+/Pz/fX76//z+/Xx9+//9fv97fn79ev7//Xh9/3v+fP59/f///P7/+3p6/Hj7/Xz/eP59/X79f/7+/n77/g=='}, 'streamSid': ''}
    # {'event': 'stop', 'sequenceNumber': '50', 'streamSid': '', 'stop': {'accountSid': '', 'callSid': ''}}