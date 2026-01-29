"""Base agent class for outbound campaigns."""

from google.adk.agents import LlmAgent


class BaseOutboundAgent(LlmAgent):
    """Base class for all outbound campaign agents.
    
    Provides:
    - Common initialization patterns
    - Shared state management
    - Context data handling
    """
    
    def __init__(self, name: str, model: str, instruction: str, tools: list, context_data: dict = None):
        """Initialize base outbound agent.
        
        Args:
            name: Agent name
            model: LLM model to use
            instruction: System instruction prompt
            tools: List of tools available to agent
            context_data: Campaign-specific context dict
        """
        self.context_data = context_data or {}
        
        # Call parent constructor
        super().__init__(
            name=name,
            model=model,
            instruction=instruction,
            tools=tools
        )
        
        # Store instruction for manual bot access (Pipecat)
        self._manual_instruction = instruction
