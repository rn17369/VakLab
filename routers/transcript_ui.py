"""
Transcript UI Router - WebSocket endpoint for UI clients to receive real-time transcripts
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from utils.transcript_manager import transcript_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ui", tags=["Transcript UI"])


@router.websocket("/transcripts")
async def transcript_websocket(websocket: WebSocket):
    """WebSocket endpoint for UI clients to receive real-time call transcripts"""
    
    logger.info("📱 UI client attempting to connect...")
    await websocket.accept()
    logger.info("✓ UI client WebSocket accepted")
    
    # Register the UI client
    await transcript_manager.register_ui_client(websocket)
    
    try:
        # Keep the connection alive and listen for any client messages
        while True:
            try:
                # Wait for messages from client (e.g., ping/pong for keepalive)
                data = await websocket.receive_json()
                
                # Handle client messages if needed (e.g., request specific call transcript)
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data.get("type") == "request_call":
                    # Client can request specific call details
                    call_sid = data.get("call_sid")
                    if call_sid and call_sid in transcript_manager.active_transcripts:
                        await websocket.send_json({
                            "type": "call_detail",
                            "data": transcript_manager.active_transcripts[call_sid]
                        })
                
            except WebSocketDisconnect:
                logger.info("UI client disconnected")
                break
            except Exception as e:
                logger.error(f"Error receiving from UI client: {e}")
                break
    
    finally:
        # Unregister the UI client
        await transcript_manager.unregister_ui_client(websocket)
        logger.info("UI client connection closed")


@router.get("/active-calls")
async def get_active_calls():
    """REST endpoint to get list of currently active calls"""
    return {
        "active_calls": list(transcript_manager.active_transcripts.values())
    }
