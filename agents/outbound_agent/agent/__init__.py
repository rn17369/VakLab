"""Agent module for ADK evaluation.

ADK expects: module.agent.root_agent
So this __init__.py must export root_agent directly.
"""
from ..orchestrator import root_agent

__all__ = ["root_agent"]
