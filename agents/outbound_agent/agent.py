import logging
from typing import AsyncGenerator
from typing_extensions import override
from google.adk.agents import LlmAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.planners import BuiltInPlanner
from google.genai import types
from .tools import end_call, send_enrollment_email

# --- Configure Loggings ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Metna Agent (The LLM) ----

class MetnaAgent(LlmAgent):
    def __init__(self, member_data=None):
        # Default fallback values
        first_name = "Raju"
        email_address = "nekadiraju@gmail.com"
        program_name = "Metna Better Care Rewards"
        zip_code = "75087"
        
        if member_data:
            first_name = member_data.get("member_first_name", first_name)
            email_address = member_data.get("member_email", email_address)
            program_name = member_data.get("campaign_name", program_name)
            zip_code = member_data.get("zip_code", zip_code)

        # Updated instructions to focus on Enrollment and Email
        instruction = f"""
# Persona & Tone
- Name: Metna, Virtual AI Breast Cancer Screening partner.
- Tone: Warm, encouraging, and clear.
- Style: Use short, conversational sentences. Avoid medical jargon.

# Core Workflow

## State 1: The Hook
- Greet the user: "Hi {first_name}, I’m Metna. I’m calling from the {program_name} to discuss your breast health. Do you have a few minutes to talk about a quick health check?"
- If "Yes" -> Move to State 2.
- If "No" -> "No problem! We can chat another time. Have a healthy day!" -> Call end_call().

## State 2: Zip Code Verification
- Action: Identify if the member is in a serviced area.
- Speech: "Wonderful. First, to find the best screening centers near you, could you please tell me your current zip code?"
- Transition: Once they provide a zip code, if it match with {zip_code} acknowledge it and move to State 3.

## State 3: The Mammogram Value Prop
- Action: Explain the benefit of the exam.
- Speech: "Thank you. I see some great centers nearby. A mammogram is just a 15-minute breast X-ray. It's the best way to catch things early when they are easiest to treat. It gives you real peace of mind. Would you like to enroll so I can send you the booking details?"
- Transition: If "Yes" or "Tell me more" -> Move to State 4.

## State 4: Enrollment & Action
- Speech: "That’s wonderful! I’m enrolling you now. I’ll send the full details and a list of local centers to your email: {email_address}. Does that sound good?"
- If "Yes" -> Call send_enrollment_email(email_address="{email_address}", first_name="{first_name}").
- After email is sent: "Excellent. You're all set! Watch for that email. Is there anything else I can help you with?"
- When the user is finished (says "no", "that's all", etc.) -> Thank them warmly and call end_call().

# Handling Objections
- Pain: "It’s normal to be nervous! It's just a few seconds of pressure. It’s very quick."
- Cost: "For most members, this is a fully covered benefit with no out-of-pocket cost."
- Catch: "No catch! We just want to help you stay healthy."

# Important
- Never mention function names like 'send_enrollment_email' to the user.
- Always use the end_call function to finish the interaction.
"""

        super().__init__(
            name="Metna",
            model="gemini-2.0-flash",  # Using stable flash model
            instruction=instruction,
            tools=[send_enrollment_email, end_call],
        )
        
        # Store instruction AFTER super().__init__ for manual bot access
        self._manual_instruction = instruction

# --- Orchestrator Agent ---

class BCSGapAgent(BaseAgent):
    def __init__(self):
        # We don't instantiate Metna here anymore because we need it per-session
        super().__init__(
            name="WarmHugTransferAgent",
            sub_agents=[] # Dynamic
        )

    def _ensure_state_safety(self, state):
        defaults = {
            "is_verified": False,
            "call_ended": False,
            "call_sid": None 
        }
        for k, v in defaults.items():
            if k not in state:
                state[k] = v

    @override
    async def _run_live_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        self._ensure_state_safety(ctx.session.state)
        
        # 1. Look up user data
        phone_number = ctx.user_id # Expecting phone number as user_id
        logging.info(f"Orchestrator starting for phone: {phone_number}")
        
        from .tools import _get_member_data
        
        # In routers/outbound_twillio.py, we stored 'member_id' and 'campaign' in the call/context
        # We need to ensure we can access them here. 
        # Typically, custom parameters from Twilio come in ctx.session.state via the websocket "customParameters"
        
        member_id = ctx.session.state.get("member_id")
        campaign_name = ctx.session.state.get("campaign")
        
        member_data = _get_member_data(phone_number, member_id, campaign_name)
        
        if member_data:
            logging.info(f"Found member: {member_data.get('member_first_name')}")
            # Inject into state just in case tools need it later
            for k, v in member_data.items():
                ctx.session.state[k] = v
        else:
            logging.warning("No member data found via DB lookup.")

        # 2. Instantiate Metna with context
        metna_agent = MetnaAgent(member_data=member_data)
        
        # 3. Run the tailored agent
        async for event in metna_agent.run_live(ctx):
            yield event
            
            # Logic to terminate if the LLM decides the conversation is over 
            # (e.g., after the handover is complete)
            if ctx.session.state.get("call_ended"):
                break

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # Logic similar to _run_live_impl but for async text chat
        self._ensure_state_safety(ctx.session.state)
        
        # 1. Lookup (Optional for text chat debug, but good to have)
        from .tools import _get_member_data
        
        phone_number = ctx.user_id 
        member_id = ctx.session.state.get("member_id")
        campaign_name = ctx.session.state.get("campaign")
        
        # Try lookup
        member_data = _get_member_data(phone_number, member_id, campaign_name)
        
        # 2. Instantiate
        metna_agent = MetnaAgent(member_data=member_data)
        
        # 3. Run
        async for event in metna_agent.run_async(ctx):
            yield event

# --- Export ---
root_agent = BCSGapAgent()