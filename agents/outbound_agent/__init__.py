"""Outbound Agent package - Multi-campaign voice bot orchestrator."""
from .orchestrator import OutboundOrchestrator, root_agent
from . import agent  # ADK eval requires this: accesses module.agent.root_agent

__all__ = ["OutboundOrchestrator", "root_agent", "agent"]
