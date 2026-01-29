"""Base agent class for outbound campaigns."""

from typing import Dict, Any, Optional
from google.adk.agents import LlmAgent
from pydantic import Field, ConfigDict


class BaseOutboundAgent(LlmAgent):
    """Base class for all outbound campaign agents.
    
    Provides:
    - Common initialization patterns
    - Shared state management
    - Context data handling
    """
    
    # Allow extra fields for context_data and _manual_instruction
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra='allow',  # Override parent's 'forbid' to allow our custom fields
    )
    
    # Declare context_data as a proper pydantic field
    context_data: Dict[str, Any] = Field(default_factory=dict)
    _manual_instruction: str = ""
    
    def __init__(self, name: str, model: str, instruction: str, tools: list, context_data: dict = None, **kwargs):
        """Initialize base outbound agent.
        
        Args:
            name: Agent name
            model: LLM model to use
            instruction: System instruction prompt
            tools: List of tools available to agent
            context_data: Campaign-specific context dict
        """
        # Call parent constructor with all required fields
        super().__init__(
            name=name,
            model=model,
            instruction=instruction,
            tools=tools,
            context_data=context_data or {},
            **kwargs
        )
        
        # Store instruction for manual bot access (Pipecat)
        object.__setattr__(self, '_manual_instruction', instruction)
