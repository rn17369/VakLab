"""Shared tools used across all campaign types."""

import logging
from google.adk.tools import ToolContext


def end_call(tool_context: ToolContext):
    """Terminates the AI agent's participation in the call (stops listening/speaking).
    
    Does NOT hang up the phone line, to ensure the customer stays connected 
    to the human agent in the conference.
    
    Shared across all campaign types.
    """
    try:
        call_sid = tool_context.state.get("call_sid")
        logging.info(f"Agent leaving conversation for Call SID: {call_sid}")
        
        # Update state ensuring loop breaks so the AI stops processing audio
        tool_context.state["call_ended"] = True
        
        return "Agent session ended. Goodbye."
    except Exception as e:
        logging.error(f"Failed to end agent session: {e}")
        tool_context.state["call_ended"] = True
        return "Agent session ended with error."
