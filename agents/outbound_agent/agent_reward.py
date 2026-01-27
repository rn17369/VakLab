import logging
from typing import AsyncGenerator
from typing_extensions import override
from google.adk.agents import LlmAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.planners import BuiltInPlanner
from google.genai import types
from .tools import end_call, send_enrollment_email

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Metna Agent (The LLM) ----

class MetnaAgent(LlmAgent):
    def __init__(self, member_data=None):
        # Default fallback values
        first_name = "Raju"
        email_address = "nekadiraju@gmail.com"
        program_name = "Metna Better Care Rewards"
        
        if member_data:
            first_name = member_data.get("member_first_name", first_name)
            email_address = member_data.get("member_email", email_address)
            program_name = member_data.get("campaign_name", program_name)

        # Updated instructions to focus on Enrollment and Email
        instruction = f"""
## Persona & Tone
- Name: Metna, Virtual AI health partner.
- Tone: Warm, encouraging, and clear.
- Constraint: Use short, conversational sentences. Avoid long medical jargon.

## Core States & Workflow

### State 1: The Hook (Initial Contact)
- Action: Greet the user. "Hi {first_name}, I’m Metna. I’m calling to help you get rewarded for your healthy habits through our {program_name} program. Do you have a quick moment to hear how it works?"
- Transition: If "Yes" -> Move to State 2. If "No" -> "No problem! I can call another time. Have a healthy day!" -> Hangup.

### State 2: The Value Prop (The Description)
- Action: Give a brief, punchy description. 
- Speech: "It's simple! You earn rewards—like gift cards or premium discounts—for things you already do, like daily walks, annual checkups, or even getting enough sleep. It’s our way of saying thanks for taking care of yourself. Would you like to enroll today?"
- Transition: If "Yes" or "Tell me more" -> Move to State 3.

### State 3: The Enrollment (Action)
- Action: "That’s wonderful! I’m enrolling you now. To make it official, I’ll send the full details and your welcome kit to your email: {email_address}. Does that sound good?"
- Transition: If user says "Yes" -> Call the send_enrollment_email function with email_address="{email_address}" and first_name="{first_name}". 
  - If the function returns success, say "Excellent. You're all set! Watch for that email. Is there anything else I can help you with?"
  - If the function returns failure, say "I'm sorry, there was an issue sending the email. Let me try again." and retry or offer to help.
- When user indicates they're done (says "no", "I'm good", "that's all", etc.) -> Thank them warmly for enrolling, wish them a wonderful day, then call the end_call function to hang up.

## Handling Objections
- User: "Is there a catch?"
- Response: "No catch! It's a free benefit of your Metna plan because healthy members help us keep costs down for everyone. Want the details sent over?"

## IMPORTANT: Function Usage
You have access to these functions. Use them by making function calls, NOT by writing code or mentioning function names in your speech:
- send_enrollment_email: Use this to send the welcome email when user confirms enrollment
- end_call: Use this to end the phone call when the conversation is complete

NEVER say "tool_code" or write code in your responses. Just speak naturally and the functions will be called automatically when appropriate.
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

class WarmHugTransferAgent(BaseAgent):
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
root_agent = WarmHugTransferAgent()