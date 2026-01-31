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
from agents.outbound_agent.orchestrator import OutboundOrchestrator

load_dotenv(override=True)


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
    logger.info(f"Starting Pipecat bot for call {call_sid} - Campaign: {campaign}")
    
    try:
        # 1. Initialize orchestrator and get campaign-specific agent
        orchestrator = OutboundOrchestrator()
        
        # Load context data based on campaign type
        context_data = orchestrator._load_context_data(to_number, member_id, campaign)
        logger.info(f"Context data loaded: {context_data}")
        
        # Get campaign-specific agent
        campaign_agent = orchestrator._get_agent_for_campaign(campaign, context_data)
        logger.info(f"Campaign agent initialized: {campaign_agent.__class__.__name__}")
        
        # 2. Get instruction from agent
        instruction = campaign_agent._manual_instruction
        
        # Extract first name for logging (handle both HEDIS and Appointment formats)
        first_name = context_data.get("member_first_name") or context_data.get("patient_name", "there").split()[0]
        logger.info(f"System instruction prepared for {first_name}")
        
        # 3. Setup Google services
        logger.info(f"Setting up Google STT service...")
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "cool-furnace-483603-b2-fdd4814415cb.json")
        logger.info(f"Using credentials from: {credentials_path}")
        stt = GoogleSTTService(
            credentials_path=credentials_path,
            sample_rate=8000,
        )
        logger.info(f"STT service created")
        
        logger.info(f"Setting up Google LLM service...")
        
        # Build tools dynamically based on campaign type
        campaign_lower = campaign.lower() if campaign else ""
        
        if "appointment" in campaign_lower:
            # Appointment tools
            from agents.outbound_agent.tools.shared import end_call
            from agents.outbound_agent.tools.appointment_tools import reschedule_appointment, send_confirmation_sms
            
            tools = [
                {
                    "function_declarations": [
                        {
                            "name": "reschedule_appointment",
                            "description": "Reschedules a patient's appointment to a new available time slot. Call this when the patient agrees to the offered appointment time.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "patient_id": {
                                        "type": "string",
                                        "description": "The patient's unique identifier"
                                    },
                                    "new_appointment_id": {
                                        "type": "string",
                                        "description": "The ID of the new appointment slot"
                                    },
                                    "original_appointment_id": {
                                        "type": "string",
                                        "description": "The ID of the original cancelled appointment"
                                    }
                                },
                                "required": ["patient_id", "new_appointment_id", "original_appointment_id"]
                            }
                        },
                        {
                            "name": "send_confirmation_sms",
                            "description": "Sends an SMS confirmation with appointment details after rescheduling. Call this after successfully rescheduling an appointment.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "phone_number": {
                                        "type": "string",
                                        "description": "The patient's phone number"
                                    },
                                    "appointment_details": {
                                        "type": "string",
                                        "description": "Details of the confirmed appointment (date, time, provider, clinic)"
                                    }
                                },
                                "required": ["phone_number", "appointment_details"]
                            }
                        },
                        {
                            "name": "end_call",
                            "description": "Ends the phone call gracefully after the conversation is complete. Call this after thanking the patient or when they want to end the call.",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    ]
                }
            ]
        else:
            # HEDIS tools (default)
            from agents.outbound_agent.tools.hedis_tools import send_enrollment_email
            from agents.outbound_agent.tools.shared import end_call
            
            # Get member email for tool usage
            member_email = context_data.get("member_email", "user@example.com")
            
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
            credentials_path=credentials_path,
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

        # 6. Build pipeline - proper flow for conversation
        # Audio -> STT -> User Aggregator -> LLM -> TTS -> Audio Out -> Assistant Aggregator
        pipeline = Pipeline(
            [
                transport.input(),
                stt,
                user_aggregator,
                llm,
                tts,
                transport.output(),
                assistant_aggregator,
            ]
        )
        logger.info(f"Pipeline created with STT->LLM->TTS flow")

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
        
        # Register function handlers based on campaign type
        # Track state for actions
        call_state = {"action_taken": False}
        
        if "appointment" in campaign_lower:
            # Appointment tool handlers
            async def handle_reschedule_appointment(params: FunctionCallParams):
                """Handle the reschedule_appointment function call"""
                args = params.arguments
                patient_id = args.get("patient_id")
                new_appointment_id = args.get("new_appointment_id")
                original_appointment_id = args.get("original_appointment_id")
                logger.info(f"[TOOL] reschedule_appointment called for patient {patient_id}")
                
                try:
                    from agents.outbound_agent.tools.appointment_tools import reschedule_appointment
                    result = reschedule_appointment(patient_id, new_appointment_id, original_appointment_id)
                    call_state["action_taken"] = True
                    logger.info(f"✓ Appointment rescheduled for patient {patient_id}")
                    await params.result_callback(result)
                except Exception as e:
                    logger.error(f"Failed to reschedule appointment: {e}")
                    await params.result_callback(f"Failed to reschedule appointment: {e}")
            
            async def handle_send_confirmation_sms(params: FunctionCallParams):
                """Handle the send_confirmation_sms function call"""
                args = params.arguments
                phone = args.get("phone_number")
                details = args.get("appointment_details")
                logger.info(f"[TOOL] send_confirmation_sms called for {phone}")
                
                try:
                    from agents.outbound_agent.tools.appointment_tools import send_confirmation_sms
                    result = send_confirmation_sms(phone, details)
                    logger.info(f"✓ Confirmation SMS sent to {phone}")
                    await params.result_callback(result)
                except Exception as e:
                    logger.error(f"Failed to send SMS: {e}")
                    await params.result_callback(f"Failed to send SMS: {e}")
            
            async def handle_end_call(params: FunctionCallParams):
                """Handle the end_call function call"""
                logger.info(f"[TOOL] end_call triggered - ending conversation")
                await params.result_callback("Call ended. Goodbye!")
                await task.queue_frames([EndFrame()])
            
            llm.register_function("reschedule_appointment", handle_reschedule_appointment)
            llm.register_function("send_confirmation_sms", handle_send_confirmation_sms)
            llm.register_function("end_call", handle_end_call)
            logger.info(f"Appointment tool handlers registered")
        else:
            # HEDIS tool handlers
            member_email = context_data.get("member_email", "user@example.com")
            
            async def handle_send_enrollment_email(params: FunctionCallParams):
                """Handle the send_enrollment_email function call"""
                args = params.arguments
                email = args.get("email_address", member_email)
                name = args.get("first_name", first_name)
                logger.info(f"[TOOL] send_enrollment_email called for {name} at {email}")
                
                try:
                    from agents.outbound_agent.tools.hedis_tools import send_enrollment_email
                    result = send_enrollment_email(email, name)
                    call_state["action_taken"] = True
                    logger.info(f"✓ Enrollment email sent to {email} for {name}")
                    await params.result_callback(f"Successfully sent enrollment email to {email}")
                except Exception as e:
                    logger.error(f"Failed to send email: {e}")
                    await params.result_callback(f"Failed to send email: {e}")
            
            async def handle_end_call(params: FunctionCallParams):
                """Handle the end_call function call"""
                logger.info(f"[TOOL] end_call triggered - ending conversation")
                await params.result_callback("Call ended. Goodbye!")
                await task.queue_frames([EndFrame()])
            
            llm.register_function("send_enrollment_email", handle_send_enrollment_email)
            llm.register_function("end_call", handle_end_call)
            logger.info(f"HEDIS tool handlers registered")
        
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
            await task.cancel()

        runner = PipelineRunner()
        logger.info(f"Starting pipeline runner...")
        await runner.run(task)
        logger.info(f"Pipeline runner completed")
        
    except Exception as ex:
        logger.error(f"ERROR in run_pipe_bot: {ex}", exc_info=True)
        raise
