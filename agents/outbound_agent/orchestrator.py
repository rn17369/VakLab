"""Orchestrator agent that routes to campaign-specific agents."""

import logging
from typing import AsyncGenerator
from typing_extensions import override
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OutboundOrchestrator(BaseAgent):
    """Routes calls to campaign-specific agents based on context."""
    
    def __init__(self):
        super().__init__(
            name="OutboundOrchestrator",
            sub_agents=[]  # Dynamic
        )

    def _ensure_state_safety(self, state):
        """Ensure required state keys exist with defaults."""
        defaults = {
            "is_verified": False,
            "call_ended": False,
            "call_sid": None 
        }
        for k, v in defaults.items():
            if k not in state:
                state[k] = v

    def _get_agent_for_campaign(self, campaign_type: str, context_data: dict):
        """Factory method to instantiate the right agent.
        
        Args:
            campaign_type: Campaign identifier from call context
            context_data: Campaign-specific data dictionary
            
        Returns:
            Campaign-specific agent instance
        """
        # Normalize campaign type
        campaign_lower = campaign_type.lower() if campaign_type else ""
        
        if "hedis" in campaign_lower or "metna" in campaign_lower or "breast" in campaign_lower:
            from .campaigns.hedis_agent import MetnaAgent
            return MetnaAgent(member_data=context_data)
        elif "appointment" in campaign_lower:
            from .campaigns.appointment_agent import AppointmentAgent
            return AppointmentAgent(context_data=context_data)
        else:
                logger.warning(f"Unknown campaign type '{campaign_type}', defaulting to HEDIS")
                from .campaigns.hedis_agent import MetnaAgent
                return MetnaAgent(member_data=context_data)

    def _load_context_data(self, phone_number: str, member_id: str, campaign_type: str):
        """Load context data based on campaign type.
        
        Args:
            phone_number: Patient/member phone number
            member_id: Patient/member ID
            campaign_type: Campaign identifier
            
        Returns:
            Context data dictionary
        """
        campaign_lower = campaign_type.lower() if campaign_type else ""
        
        if "appointment" in campaign_lower:
            from .data.appointment_context import _get_appointment_data
            return _get_appointment_data(phone_number, member_id)
        else:
            # Default to HEDIS context loader
            from .data.hedis_context import _get_member_data
            return _get_member_data(phone_number, member_id, campaign_type)

    @override
    async def _run_live_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        self._ensure_state_safety(ctx.session.state)
        
        # 1. Extract call context
        phone_number = ctx.user_id  # Expecting phone number as user_id
        member_id = ctx.session.state.get("member_id")
        
        # Detect campaign from session.app_name (set by evalset or runner)
        app_name = ctx.session.app_name or ""
        campaign_type = ctx.session.state.get("campaign")
        if not campaign_type:
            if "appointment" in app_name.lower():
                campaign_type = "appointment_backfill"
            else:
                campaign_type = "hedis_gap_closure"
        
        logging.info(f"Orchestrator starting for phone: {phone_number}, campaign: {campaign_type}")
        
        # 2. Load campaign-specific context
        context_data = self._load_context_data(phone_number, member_id, campaign_type)
        
        if context_data:
            logging.info(f"Found context for: {context_data.get('member_first_name') or context_data.get('patient_first_name')}")
            # Inject into state for tools
            for k, v in context_data.items():
                ctx.session.state[k] = v
        else:
            logging.warning("No context data found via DB lookup.")

        # 3. Instantiate campaign-specific agent
        agent = self._get_agent_for_campaign(campaign_type, context_data)
        
        # 4. Run the agent
        async for event in agent.run_live(ctx):
            yield event
            
            # Terminate if call ended
            if ctx.session.state.get("call_ended"):
                break

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Async text chat implementation."""
        self._ensure_state_safety(ctx.session.state)
        
        # 1. Extract context
        phone_number = ctx.user_id 
        member_id = ctx.session.state.get("member_id")
        
        # Detect campaign from session.app_name (set by evalset or runner)
        # ADK stores app_name as a direct session attribute, not in state
        app_name = ctx.session.app_name or ""
        logger.info(f"Orchestrator: app_name from session: '{app_name}'")
        
        campaign_type = ctx.session.state.get("campaign")
        if not campaign_type:
            # Infer from app_name (e.g., "appointment_backfill")
            if "appointment" in app_name.lower():
                campaign_type = "appointment_backfill"
            else:
                campaign_type = "hedis_gap_closure"
        
        logger.info(f"Orchestrator: Using campaign_type: {campaign_type}")
        
        # 2. Load context
        context_data = self._load_context_data(phone_number, member_id, campaign_type)
        
        # 3. Instantiate agent
        agent = self._get_agent_for_campaign(campaign_type, context_data)
        
        # 4. Run
        async for event in agent.run_async(ctx):
            yield event


# --- Export ---
root_agent = OutboundOrchestrator()
