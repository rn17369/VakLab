"""
Transcript Manager - Manages real-time call transcripts and broadcasts to UI clients
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Set, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class TranscriptManager:
    """Manages active call transcripts and broadcasts events to connected UI clients"""
    
    def __init__(self):
        # Store active transcripts: call_sid -> transcript data
        self.active_transcripts: Dict[str, Dict[str, Any]] = {}
        
        # Store connected UI WebSocket clients
        self.ui_clients: Set[WebSocket] = set()
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def register_ui_client(self, websocket: WebSocket):
        """Register a new UI client WebSocket connection"""
        async with self._lock:
            self.ui_clients.add(websocket)
            logger.info(f"UI client connected. Total clients: {len(self.ui_clients)}")
            
            # Send current active transcripts to the new client
            await self._send_to_client(websocket, {
                "type": "init",
                "active_calls": list(self.active_transcripts.values())
            })
    
    async def unregister_ui_client(self, websocket: WebSocket):
        """Unregister a UI client WebSocket connection"""
        async with self._lock:
            self.ui_clients.discard(websocket)
            logger.info(f"UI client disconnected. Total clients: {len(self.ui_clients)}")
    
    async def start_call(self, call_sid: str, member_data: Dict[str, Any] = None):
        """Initialize a new call transcript session"""
        async with self._lock:
            self.active_transcripts[call_sid] = {
                "call_sid": call_sid,
                "member_data": member_data or {},
                "status": "active",
                "start_time": datetime.utcnow().isoformat(),
                "messages": []
            }
            logger.info(f"Started transcript for call {call_sid}")
        
        # Broadcast to UI clients
        await self._broadcast({
            "type": "call_started",
            "call_sid": call_sid,
            "data": self.active_transcripts[call_sid]
        })
    
    async def add_transcript_message(self, call_sid: str, speaker: str, text: str, message_type: str = "text"):
        """Add a transcript message to an active call"""
        async with self._lock:
            if call_sid not in self.active_transcripts:
                logger.warning(f"Call {call_sid} not found in active transcripts")
                return
            
            message = {
                "timestamp": datetime.utcnow().isoformat(),
                "speaker": speaker,  # "AI" or "Customer"
                "text": text,
                "type": message_type  # "text", "tool_call", "system"
            }
            
            self.active_transcripts[call_sid]["messages"].append(message)
            logger.info(f"[{call_sid}] {speaker}: {text[:100]}...")
        
        # Broadcast to UI clients
        await self._broadcast({
            "type": "transcript_message",
            "call_sid": call_sid,
            "message": message
        })
    
    async def end_call(self, call_sid: str, reason: str = "completed"):
        """Mark a call as ended"""
        async with self._lock:
            if call_sid in self.active_transcripts:
                self.active_transcripts[call_sid]["status"] = "ended"
                self.active_transcripts[call_sid]["end_time"] = datetime.utcnow().isoformat()
                self.active_transcripts[call_sid]["end_reason"] = reason
                logger.info(f"Ended transcript for call {call_sid}: {reason}")
        
        # Broadcast to UI clients
        await self._broadcast({
            "type": "call_ended",
            "call_sid": call_sid,
            "reason": reason
        })
        
        # Optional: Clean up after some time
        await asyncio.sleep(60)  # Keep for 1 minute after end
        async with self._lock:
            if call_sid in self.active_transcripts:
                del self.active_transcripts[call_sid]
                logger.info(f"Cleaned up transcript for call {call_sid}")
    
    async def update_call_status(self, call_sid: str, status: str, metadata: Dict[str, Any] = None):
        """Update call status (e.g., 'ringing', 'active', 'ended')"""
        async with self._lock:
            if call_sid in self.active_transcripts:
                self.active_transcripts[call_sid]["status"] = status
                if metadata:
                    self.active_transcripts[call_sid].update(metadata)
        
        # Broadcast to UI clients
        await self._broadcast({
            "type": "call_status_update",
            "call_sid": call_sid,
            "status": status,
            "metadata": metadata or {}
        })
    
    async def _broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected UI clients"""
        if not self.ui_clients:
            return
        
        disconnected_clients = set()
        
        for client in self.ui_clients:
            try:
                await client.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to UI client: {e}")
                disconnected_clients.add(client)
        
        # Clean up disconnected clients
        if disconnected_clients:
            async with self._lock:
                self.ui_clients -= disconnected_clients
    
    async def _send_to_client(self, client: WebSocket, message: Dict[str, Any]):
        """Send a message to a specific client"""
        try:
            await client.send_json(message)
        except Exception as e:
            logger.error(f"Error sending to specific UI client: {e}")


# Global singleton instance
transcript_manager = TranscriptManager()
