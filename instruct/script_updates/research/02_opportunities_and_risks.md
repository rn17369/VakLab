# Opportunities, Risks & Duplication Analysis

## 🎯 Opportunities You Might Not Be Considering

### 1. **Single Orchestrator, Multiple Personas (Factory Pattern)**

The current `BCSGapAgent` already dynamically instantiates `MetnaAgent` based on context. This pattern can be extended WITHOUT creating separate agent folders:

```python
# Current approach (already in agent.py)
metna_agent = MetnaAgent(member_data=member_data)

# Extended approach
if campaign_type == "hedis_gap_closure":
    agent = HedisAgent(context_data)
elif campaign_type == "appointment_backfill":
    agent = AppointmentAgent(context_data)
```

**Why this matters**: ADK expects ONE `root_agent` per agent folder. Creating separate folders means separate ADK apps, separate eval runs, separate deployments. Keeping one orchestrator that spawns different LLM agents is MORE aligned with your current architecture.

### 2. **Instruction Templates in Database/Config**

Instead of hardcoding instructions in Python classes, store them in:
- A `campaign_scripts` table in PostgreSQL, OR
- JSON/YAML config files per campaign

**Benefits**:
- Non-developers can update scripts
- A/B testing different script versions
- Version control on scripts separate from code
- Same agent class, different instructions

### 3. **Tool Registry Pattern**

Current `pipe_bot.py` manually registers tools:
```python
llm.register_function("send_enrollment_email", handle_send_enrollment_email)
llm.register_function("end_call", handle_end_call)
```

Could become:
```python
for tool_name, handler in CAMPAIGN_TOOLS[campaign_type].items():
    llm.register_function(tool_name, handler)
```

### 4. **Unified Context Data Model**

Instead of separate `_get_member_data()` and `_get_appointment_data()` functions, create a unified context loader:

```python
def get_call_context(phone_number, campaign_type, entity_id):
    """Returns campaign-specific context in standardized format"""
    if campaign_type == "hedis":
        return load_hedis_context(...)
    elif campaign_type == "appointment":
        return load_appointment_context(...)
```

---

## ⚠️ Duplication Risks

### 1. **Orchestrator Logic Duplication**

If you create `agents/appointment_agent/agent.py`, you'll likely copy:
- `_ensure_state_safety()` method
- `_run_live_impl()` structure
- `_run_async_impl()` structure
- State management patterns

**Better**: Keep ONE orchestrator class that delegates to campaign-specific LLM agents.

### 2. **Tool Duplication**

These tools are campaign-agnostic and should be shared:
- `end_call()` — identical for all campaigns
- DB connection utilities
- State management helpers

**Risk**: If you create `appointment_agent/tools.py`, you'll duplicate `end_call`.

### 3. **Eval Config Duplication**

Current rubrics that apply to ALL campaigns:
- `warm_tone` — universal
- `concise_responses` — universal
- `end_call_appropriate` — universal

**Better**: Create base eval config + campaign-specific overlays.

### 4. **Pipecat Integration**

`pipe_bot.py` currently imports directly:
```python
from agents.outbound_agent.agent import MetnaAgent
```

Creating separate folders means updating this import logic or duplicating the entire pipe_bot pattern.

---

## 🚨 Risks Not Being Considered

### 1. **ADK Single Root Agent Constraint**

ADK's eval framework (`adk eval`) expects:
```
agents/<folder>/__init__.py → exports root_agent
```

If you create `agents/appointment_agent/`, you need a SEPARATE eval command:
```bash
adk eval agents/outbound_agent metna_eval_set    # HEDIS
adk eval agents/appointment_agent appt_eval_set  # Appointment
```

This fragments your evaluation pipeline and makes cross-campaign comparison harder.

### 2. **Campaign Routing Before Agent Selection**

The current flow is:
```
Twilio → /voice-entry → pipe_bot.py → MetnaAgent
```

For multi-campaign, you need routing BEFORE instantiating the agent. Currently `campaign` is passed through but not used for agent selection.

### 3. **Database Schema Drift**

If HEDIS uses `target_members_detail` and Appointment uses `appointments`, you now have:
- Two different data models
- Two different lookup functions
- Two different mock data files
- Potential for schema inconsistency

### 4. **Eval Result Fragmentation**

Current `eval_runs` table has `scenario_name` but no `campaign_type` field. If you run evals for both campaigns, you can't easily filter/compare by campaign.

### 5. **Twilio Call Queue Split**

Currently one queue: `campaign_target_member_call_list`

For appointment backfill, you either:
- Add appointment calls to same table (schema changes needed), OR
- Create separate `appointment_call_queue` table (routing logic needed)

---

## ✅ Recommended Architecture (Minimal Duplication)

```
agents/
├── outbound_agent/
│   ├── __init__.py              # Exports root_agent (orchestrator)
│   ├── orchestrator.py          # Renamed from agent.py - handles routing
│   ├── campaigns/
│   │   ├── __init__.py
│   │   ├── hedis_agent.py       # HedisAgent (LlmAgent subclass)
│   │   ├── appointment_agent.py # AppointmentAgent (LlmAgent subclass)
│   │   └── base_agent.py        # Shared base class
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── shared.py            # end_call, common utilities
│   │   ├── hedis_tools.py       # send_enrollment_email
│   │   └── appointment_tools.py # reschedule_appointment, send_sms
│   ├── data/
│   │   ├── hedis_context.py     # _get_member_data
│   │   └── appointment_context.py # _get_appointment_data
│   ├── metna_eval_set.evalset.json
│   └── appointment_eval_set.evalset.json
```

**Key Principles**:
1. ONE `root_agent` (orchestrator) that routes to campaign-specific LLM agents
2. Shared tools extracted to `tools/shared.py`
3. Campaign-specific tools in dedicated files
4. Context loaders separated but follow same interface
5. All eval sets live in same agent folder for unified testing

---

## 📋 Revised Task List

| # | Task | Rationale |
|---|------|-----------|
| 1 | Restructure `agents/outbound_agent/` into campaigns/tools/data subfolders | Organization without breaking ADK |
| 2 | Create `orchestrator.py` with campaign routing logic | Central routing point |
| 3 | Extract `end_call` to `tools/shared.py` | Eliminate duplication |
| 4 | Create `campaigns/base_agent.py` with shared patterns | DRY principle |
| 5 | Create `campaigns/appointment_agent.py` | New campaign |
| 6 | Add `clinic_scheduler.sql` for mock appointment data | Data layer |
| 7 | Create `data/appointment_context.py` | Context loader |
| 8 | Create `tools/appointment_tools.py` | Campaign tools |
| 9 | Update `pipe_bot.py` for campaign routing | Integration |
| 10 | Create `appointment_eval_set.evalset.json` | Testing |
| 11 | Create shared + campaign-specific eval configs | Modular rubrics |
| 12 | Add `campaign_type` to `eval_runs` table | Analytics |

---

*See `03_task_breakdown.md` for detailed implementation plan*
