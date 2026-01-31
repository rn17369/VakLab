import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any

from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.frames.frames import LLMFullResponseStartFrame, EndFrame
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.google.tts import GoogleTTSService
from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.google.stt import GoogleSTTService
from pipecat.services.llm_service import FunctionCallParams
from fastapi import WebSocket
from pipecat.transports.websocket.fastapi import FastAPIWebsocketTransport, FastAPIWebsocketParams

# Project imports
from agents.outbound_agent.agent import MetnaAgent
from agents.outbound_agent.tools import _get_member_data
from utils.transcript_manager import transcript_manager

load_dotenv(override=True)


# Custom processor to capture and broadcast transcripts
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.frames.frames import (
    Frame,
    TranscriptionFrame,
    TextFrame,
    LLMResponseStartFrame,
    LLMResponseEndFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
)


class TranscriptCaptureProcessor(FrameProcessor):
    """Captures STT and LLM output frames and broadcasts to UI"""
    
    def __init__(self, call_sid: str):
        super().__init__()
        self.call_sid = call_sid
        self._current_llm_response = ""
        self._is_capturing_llm = False
    
    async def process_frame(self, frame: Frame, direction):
        # Capture user speech (STT output)
        if isinstance(frame, TranscriptionFrame):
            text = frame.text.strip()
            if text:
                logger.info(f"[TRANSCRIPT-STT] Customer: {text}")
                await transcript_manager.add_transcript_message(
                    self.call_sid,
                    speaker="Customer",
                    text=text,
                    message_type="speech"
                )
        
        # Capture AI responses (LLM output)
        elif isinstance(frame, LLMResponseStartFrame):
            self._is_capturing_llm = True
            self._current_llm_response = ""
        
        elif isinstance(frame, TextFrame) and self._is_capturing_llm:
            self._current_llm_response += frame.text
        
        elif isinstance(frame, LLMResponseEndFrame):
            if self._current_llm_response.strip():
                logger.info(f"[TRANSCRIPT-LLM] AI: {self._current_llm_response}")
                await transcript_manager.add_transcript_message(
                    self.call_sid,
                    speaker="AI",
                    text=self._current_llm_response,
                    message_type="speech"
                )
            self._is_capturing_llm = False
            self._current_llm_response = ""
        
        # Pass frame through to next processor
        await self.push_frame(frame, direction)


async def run_pipe_bot(
    websocket: WebSocket,
    stream_sid: str,
    call_sid: str,
    to_number: str = None,
    from_number: str = None,
    member_id: str = None,
    campaign: str = None,
):
    """Main bot entry point using Pipecat framework."""
    logger.info(f"Starting Pipecat bot for call {call_sid}")
    
    try:
        # 1. Lookup member data
        member_data = _get_member_data(to_number, member_id, campaign)
        logger.info(f"Member data: {member_data}")
        
        # Initialize transcript for this call
        await transcript_manager.start_call(call_sid, member_data)
        
        metna_agent = MetnaAgent(member_data=member_data)
        logger.info(f"Agent initialized")
        
        # 2. Get instruction from agent (greeting is already included in State 1)
        # NOTE: Removed duplicate greeting logic - greeting is already in agent's State 1
        # first_name = member_data.get("member_first_name", "there") if member_data else "there"
        # campaign_name = member_data.get("campaign_name", "program") if member_data else "program"
        # logger.info(f"First name: {first_name}, Campaign: {campaign_name}")
        # greeting = f"Hi {first_name}, I'm Metna. I'm calling to help you get rewarded for our {campaign_name}. Do you have a moment?"
        # instruction = metna_agent._manual_instruction + f"\n\nStart the conversation with this greeting: {greeting}"
        instruction = metna_agent._manual_instruction
        first_name = member_data.get("member_first_name", "there") if member_data else "there"  # Still needed for logging
        logger.info(f"System instruction prepared")
        
        # 3. Setup Google services
        logger.info(f"Setting up Google STT service...")
        stt = GoogleSTTService(
            credentials_path="/Users/rn/Documents/gcp_hackthon/cool-furnace-483603-b2-fdd4814415cb.json",
            sample_rate=8000,
        )
        logger.info(f"STT service created")
        
        logger.info(f"Setting up Google LLM service...")
        
        # Get member email for tool usage
        member_email = member_data.get("member_email", "user@example.com") if member_data else "user@example.com"
        
        # Define tools for the LLM (Google format)
        tools = [
            {
                "function_declarations": [
                    {
                        "name": "send_enrollment_email",
                        "description": "Sends a welcome enrollment email to the member after they confirm enrollment. Call this when the user agrees to enroll and confirms their email.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "email_address": {
                                    "type": "string",
                                    "description": "The email address to send the enrollment email to"
                                },
                                "first_name": {
                                    "type": "string", 
                                    "description": "The first name of the member for personalization"
                                }
                            },
                            "required": ["email_address", "first_name"]
                        }
                    },
                    {
                        "name": "end_call",
                        "description": "Ends the phone call gracefully after the conversation is complete. Call this after thanking the user or when the user wants to end the call.",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                ]
            }
        ]
        
        llm = GoogleLLMService(
            model="gemini-3-flash-preview",  # Using Gemini 3 for hackathon
            api_key=os.getenv("GOOGLE_API_KEY"),
            system_instruction=instruction,
            tools=tools
        )
        logger.info(f"LLM service created with tools")

        logger.info(f"Setting up Google TTS service...")
        tts = GoogleTTSService(
            credentials_path="/Users/rn/Documents/gcp_hackthon/cool-furnace-483603-b2-fdd4814415cb.json",
            voice_id="en-US-Journey-F",  # Female voice
            sample_rate=8000
        )
        logger.info(f"TTS service created with female voice")

        # 4. Setup context using LLMContext and LLMContextAggregatorPair
        messages = [
            {
                "role": "system",
                "content": instruction,
            },
        ]
        context = LLMContext(messages)
        user_aggregator, assistant_aggregator = LLMContextAggregatorPair(context)
        logger.info(f"Context aggregator pair created")

        # 5. Setup transport
        account_sid = os.getenv("TWILIO_SID")
        auth_token = os.getenv("TWILIO_AUTH")
        logger.info(f"Twilio credentials: account_sid={account_sid}")
        
        serializer = TwilioFrameSerializer(
            stream_sid=stream_sid,
            call_sid=call_sid,
            account_sid=account_sid,
            auth_token=auth_token,
        )
        logger.info(f"Serializer created")

        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                add_wav_header=False,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.5)),
                serializer=serializer,
            ),
        )
        logger.info(f"Transport created")

        # 6. Build pipeline - proper flow for conversation with transcript capture
        # Create transcript capture processor
        transcript_processor = TranscriptCaptureProcessor(call_sid)
        
        # Audio -> STT -> User Aggregator -> Transcript Capture -> LLM -> TTS -> Audio Out -> Assistant Aggregator
        pipeline = Pipeline(
            [
                transport.input(),
                stt,
                user_aggregator,
                transcript_processor,  # Capture transcripts here
                llm,
                tts,
                transport.output(),
                assistant_aggregator,
            ]
        )
        logger.info(f"Pipeline created with STT->Transcript->LLM->TTS flow")

        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                audio_in_sample_rate=8000,
                audio_out_sample_rate=8000,
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
        )
        logger.info(f"PipelineTask created")
        
        # Register function handlers for tools
        # Track state for email sent
        call_state = {"is_emailed": False}
        
        async def handle_send_enrollment_email(params: FunctionCallParams):
            """Handle the send_enrollment_email function call"""
            args = params.arguments
            email = args.get("email_address", member_email)
            name = args.get("first_name", first_name)
            logger.info(f"[TOOL] send_enrollment_email called for {name} at {email}")
            
            try:
                # Import and call actual email sending function
                from agents.outbound_agent.tools import send_enrollment_email as send_email_func
                result = send_email_func(email, name)
                
                # Track that email was sent
                call_state["is_emailed"] = True
                
                logger.info(f"✓ Enrollment email sent to {email} for {name}")
                
                # Add to transcript
                await transcript_manager.add_transcript_message(
                    call_sid,
                    speaker="System",
                    text=f"📧 Enrollment email sent to {email}",
                    message_type="tool_call"
                )
                
                await params.result_callback(f"Successfully sent enrollment email to {email}")
            except Exception as e:
                logger.error(f"Failed to send email: {e}")
                await params.result_callback(f"Failed to send email: {e}")
        
        async def handle_end_call(params: FunctionCallParams):
            """Handle the end_call function call"""
            logger.info(f"[TOOL] end_call triggered - ending conversation")
            
            # Add to transcript
            await transcript_manager.add_transcript_message(
                call_sid,
                speaker="System",
                text="📞 Call ended by AI",
                message_type="system"
            )
            
            await params.result_callback("Call ended. Goodbye!")
            # Queue EndFrame to terminate the pipeline
            await task.queue_frames([EndFrame()])
        
        llm.register_function("send_enrollment_email", handle_send_enrollment_email)
        llm.register_function("end_call", handle_end_call)
        logger.info(f"Tool handlers registered: send_enrollment_email, end_call")
        
        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            logger.info(f"[EVENT] Pipecat bot connected for {first_name}")
            # For outbound calls, bot should greet first
            # Add user message to context to prompt the LLM
            context.add_message({"role": "user", "content": "Start the call now and greet me."})
            # Trigger LLM to generate response
            await task.queue_frames([LLMFullResponseStartFrame()])
            logger.info(f"[GREETING] Triggered LLM to generate greeting")

        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            logger.info(f"[EVENT] Pipecat bot call ended for {call_sid}")
            await transcript_manager.end_call(call_sid, reason="disconnected")
            await task.cancel()

        runner = PipelineRunner()
        logger.info(f"Starting pipeline runner...")
        await runner.run(task)
        logger.info(f"Pipeline runner completed")
        
    except Exception as ex:
        logger.error(f"ERROR in run_pipe_bot: {ex}", exc_info=True)
        raise
