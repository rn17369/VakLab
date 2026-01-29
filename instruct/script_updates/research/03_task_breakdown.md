# Task Breakdown: Multi-Campaign Agent Architecture

## Overview

Refactor `agents/outbound_agent/` to support multiple campaign types (HEDIS + Appointment Backfill) while maintaining a single orchestrator and unified eval pipeline.

---

## Phase 1: Foundation & Restructure

### Task 1.1: Create Folder Structure
**Goal**: Organize existing code into submodules without breaking functionality

```
agents/outbound_agent/
├── __init__.py                    # Keep as-is (exports root_agent)
├── orchestrator.py                # NEW: Rename/refactor from agent.py
├── campaigns/
│   ├── __init__.py
│   ├── base.py                    # NEW: Shared LlmAgent patterns
│   └── hedis_agent.py             # MOVE: Extract MetnaAgent here
├── tools/
│   ├── __init__.py
│   ├── shared.py                  # NEW: end_call + utilities
│   └── hedis_tools.py             # MOVE: send_enrollment_email
├── data/
│   ├── __init__.py
│   └── hedis_context.py           # MOVE: _get_member_data
├── golden_convo/                  # Keep as-is
├── metna_eval_set.evalset.json    # Keep as-is
└── .adk/                          # Keep as-is
```

**Files to create**:
- `campaigns/__init__.py`
- `campaigns/base.py`
- `campaigns/hedis_agent.py`
- `tools/__init__.py`
- `tools/shared.py`
- `tools/hedis_tools.py`
- `data/__init__.py`
- `data/hedis_context.py`

**Files to modify**:
- `agent.py` → rename to `orchestrator.py` and update imports
- `__init__.py` → update import path

**Files to delete** (after migration):
- `tools.py` (code moved to `tools/` folder)

---

### Task 1.2: Extract Shared Tools
**Goal**: Move `end_call` to shared module

**From** (`tools.py`):
```python
def end_call(tool_context: ToolContext):
    """Terminates the AI agent's participation in the call..."""
```

**To** (`tools/shared.py`):
```python
from google.adk.tools import ToolContext
import logging

def end_call(tool_context: ToolContext):
    """Terminates the AI agent's participation in the call.
    
    Shared across all campaign types.
    """
    ...
```

---

### Task 1.3: Extract HEDIS Agent
**Goal**: Move `MetnaAgent` class to `campaigns/hedis_agent.py`

**Key changes**:
- Import tools from `..tools.hedis_tools`
- Import `end_call` from `..tools.shared`
- Keep instruction generation logic intact
- **Keep class name as `MetnaAgent`** (brand name)


---

### Task 1.4: Create Base Agent Class
**Goal**: Extract common patterns to `campaigns/base.py`

```python
from google.adk.agents import LlmAgent

class BaseOutboundAgent(LlmAgent):
    """Base class for all outbound campaign agents.
    
    Provides:
    - Common initialization patterns
    - Shared state management
    - Instruction template loading (future)
    """
    
    def __init__(self, name: str, context_data: dict = None):
        self.context_data = context_data or {}
        # Subclasses call super().__init__() with their specific config
```

---

### Task 1.5: Update Orchestrator
**Goal**: Refactor `BCSGapAgent` to route by campaign type

```python
# orchestrator.py

class OutboundOrchestrator(BaseAgent):
    """Routes calls to campaign-specific agents based on context."""
    
    def _get_agent_for_campaign(self, campaign_type: str, context_data: dict):
        """Factory method to instantiate the right agent."""
        if campaign_type in ["hedis_gap_closure", "Metna Breast Screening Partner Program"]:
            from .campaigns.hedis_agent import HedisAgent
            return HedisAgent(context_data)
        elif campaign_type == "appointment_backfill":
            from .campaigns.appointment_agent import AppointmentAgent
            return AppointmentAgent(context_data)
        else:
            # Default fallback
            from .campaigns.hedis_agent import HedisAgent
            return HedisAgent(context_data)
```

---

### Task 1.6: Update Imports & Verify
**Goal**: Ensure existing functionality works after restructure

**Test checklist**:
- [ ] `from agents.outbound_agent import root_agent` works
- [ ] `adk eval agents/outbound_agent metna_eval_set` passes
- [ ] `/outbound-call` endpoint works with HEDIS campaign

---

## Phase 2: Database & Context Layer

### Task 2.1: Create Clinic Scheduler Schema
**Goal**: Add mock data for appointment backfill

**New file**: `db-init/clinic_scheduler.sql`

```sql
-- Clinic/Provider Structure
CREATE TABLE IF NOT EXISTS clinics (
    clinic_id VARCHAR(50) PRIMARY KEY,
    clinic_name VARCHAR(200) NOT NULL,
    address VARCHAR(500),
    phone VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS providers (
    provider_id VARCHAR(50) PRIMARY KEY,
    clinic_id VARCHAR(50) REFERENCES clinics(clinic_id),
    provider_name VARCHAR(200) NOT NULL,
    specialty VARCHAR(100)
);

-- Patient records (separate from HEDIS members)
CREATE TABLE IF NOT EXISTS patients (
    patient_id VARCHAR(50) PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(200)
);

-- Appointments
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES patients(patient_id),
    provider_id VARCHAR(50) REFERENCES providers(provider_id),
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status VARCHAR(50) DEFAULT 'scheduled',  -- scheduled, completed, cancelled, rescheduled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Backfill queue (cancellation slots to fill)
CREATE TABLE IF NOT EXISTS appointment_backfill_queue (
    queue_id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES patients(patient_id),
    phone_number VARCHAR(20) NOT NULL,
    original_appointment_id VARCHAR(50) REFERENCES appointments(appointment_id),
    available_slot_date DATE NOT NULL,
    available_slot_time TIME NOT NULL,
    provider_id VARCHAR(50) REFERENCES providers(provider_id),
    call_status VARCHAR(50) DEFAULT 'Not Called',
    campaign_type VARCHAR(100) DEFAULT 'appointment_backfill'
);

-- Seed data
INSERT INTO clinics (clinic_id, clinic_name, address, phone)
VALUES ('CLINIC001', 'Northview Family Medicine', '123 Health Ave, Plano TX 75087', '972-555-0100')
ON CONFLICT DO NOTHING;

INSERT INTO providers (provider_id, clinic_id, provider_name, specialty)
VALUES ('PROV001', 'CLINIC001', 'Dr. Sarah Patel', 'Family Medicine')
ON CONFLICT DO NOTHING;

INSERT INTO patients (patient_id, phone_number, first_name, last_name, email)
VALUES ('PAT001', '9135960926', 'Mark', 'Reynolds', 'mark.reynolds@email.com')
ON CONFLICT DO NOTHING;

-- Original appointment (Feb 3)
INSERT INTO appointments (appointment_id, patient_id, provider_id, appointment_date, appointment_time, status)
VALUES ('APPT001', 'PAT001', 'PROV001', '2026-02-03', '10:00:00', 'scheduled')
ON CONFLICT DO NOTHING;

-- Backfill opportunity (Feb 1 cancellation slot)
INSERT INTO appointment_backfill_queue (patient_id, phone_number, original_appointment_id, available_slot_date, available_slot_time, provider_id)
VALUES ('PAT001', '9135960926', 'APPT001', '2026-02-01', '14:30:00', 'PROV001')
ON CONFLICT DO NOTHING;
```

---

### Task 2.2: Create Appointment Context Loader
**Goal**: `data/appointment_context.py` with `_get_appointment_data()`

```python
def _get_appointment_data(phone_number: str, patient_id: str = None) -> dict:
    """Fetch appointment backfill context from DB.
    
    Returns:
        {
            "patient_id": "PAT001",
            "patient_first_name": "Mark",
            "patient_last_name": "Reynolds",
            "clinic_name": "Northview Family Medicine",
            "provider_name": "Dr. Sarah Patel",
            "original_date": "2026-02-03",
            "original_time": "10:00 AM",
            "available_date": "2026-02-01",
            "available_time": "2:30 PM",
            "phone_number": "9135960926"
        }
    """
```

---

### Task 2.3: Update docker-compose.yml
**Goal**: Ensure new SQL file is loaded on init

```yaml
volumes:
  - ./db-init:/docker-entrypoint-initdb.d
```

Files in `db-init/` are executed alphabetically. Rename or prefix:
- `01_init.sql` (member data)
- `02_eval_schema.sql`
- `03_clinic_scheduler.sql`

---

## Phase 3: Appointment Agent Implementation

### Task 3.1: Create Appointment Tools
**Goal**: `tools/appointment_tools.py`

```python
def reschedule_appointment(patient_id: str, new_date: str, new_time: str) -> bool:
    """Updates appointment in DB and cancels original slot."""
    
def send_confirmation_sms(phone_number: str, message: str) -> bool:
    """Sends SMS via Twilio."""
```

---

### Task 3.2: Create Appointment Golden Conversations
**Goal**: `golden_convo/` reference files for appointment scenarios

Create reference conversations that demonstrate ideal agent behavior for common appointment scenarios. These serve as:
- Training reference for instruction design
- Baseline for eval scenario creation
- Documentation of expected objection handling

**Files to create**:

**`golden_convo/appt_happy_path.json`**
- Patient accepts earlier slot quickly
- Confirms reschedule
- Gets SMS confirmation

**`golden_convo/appt_last_minute_objection.json`**
- Patient hesitates ("too last minute")
- Agent reassures original stays
- Patient reconsiders and accepts
- OR patient declines gracefully

**`golden_convo/appt_billing_concern.json`**
- Patient asks "Will this affect my copay?" or "Is there a cancellation fee?"
- Agent clarifies no additional charges
- Patient proceeds or declines

**`golden_convo/appt_needs_to_reschedule_again.json`**
- Patient accepted but then realizes conflict
- Asks to change to different time
- Agent handles gracefully (either offers alternative or keeps original)

**`golden_convo/appt_busy_callback.json`**
- Patient can't talk
- Agent offers callback
- Clean exit

---

### Task 3.3: Create Appointment Agent
**Goal**: `campaigns/appointment_agent.py`

```python
class AppointmentAgent(BaseOutboundAgent):
    def __init__(self, context_data: dict = None):
        # Extract context
        patient_name = context_data.get("patient_first_name", "there")
        clinic_name = context_data.get("clinic_name", "the clinic")
        provider_name = context_data.get("provider_name", "your provider")
        available_date = context_data.get("available_date")
        available_time = context_data.get("available_time")
        original_date = context_data.get("original_date")
        
        instruction = f"""
# Persona & Tone
- Role: Scheduling assistant for {clinic_name}
- Tone: Friendly, efficient, respectful of time

# Core Workflow

## State 1: Introduction
- "Hi {patient_name} — I'm calling from {clinic_name}. Is now a good time?"
- If "No" -> "No problem! We'll try again later." -> Call end_call()

## State 2: Offer Earlier Slot
- "We had a cancellation for {provider_name} on {available_date} at {available_time}. Would that work better than your appointment on {original_date}?"
- If interested -> Move to State 3
- If declines -> "No worries, your original appointment stays as scheduled. Have a great day!" -> end_call()

## State 3: Confirm & Update
- Call reschedule_appointment()
- "Great, you're confirmed for {available_date} at {available_time} with {provider_name}."
- Call send_confirmation_sms()
- "You'll get a confirmation text shortly. Anything else I can help with?"
- When done -> end_call()

# Objection Handling
- "Too last minute": "Totally understand. Your original appointment stays exactly as scheduled. Would you like to keep it as is?"
- "Need to check schedule": "Of course! Take your time, I'll wait."
- "Billing/cost concern": "There's no additional charge or cancellation fee for moving to an earlier slot. Your copay stays the same."
- "Changed mind after accepting": "No problem at all. I can keep your original appointment on {original_date} if that works better."
"""
        
        super().__init__(
            name="SchedulingAssistant",
            model="gemini-2.0-flash",
            instruction=instruction,
            tools=[reschedule_appointment, send_confirmation_sms, end_call]
        )
```

---

### Task 3.4: Update Orchestrator Routing
**Goal**: Add appointment campaign to routing logic

```python
def _get_agent_for_campaign(self, campaign_type: str, context_data: dict):
    if campaign_type in ["hedis_gap_closure", "Metna Breast Screening Partner Program"]:
        from .campaigns.hedis_agent import MetnaAgent  # Keep brand name
        return MetnaAgent(context_data)
    elif campaign_type == "appointment_backfill":
        from .campaigns.appointment_agent import AppointmentAgent
        return AppointmentAgent(context_data)
```

---

### Task 3.5: Update pipe_bot.py
**Goal**: Route to correct agent based on campaign

```python
# Current (hardcoded):
from agents.outbound_agent.agent import MetnaAgent
metna_agent = MetnaAgent(member_data=member_data)

# New (dynamic):
from agents.outbound_agent.orchestrator import get_agent_for_campaign
agent = get_agent_for_campaign(campaign, context_data)
```

Also update tool registration to be dynamic based on campaign.

---

## Phase 4: Evaluation Framework

### Task 4.1: Create Appointment Eval Set
**Goal**: `appointment_eval_set.evalset.json`

```json
{
  "eval_set_id": "appointment_eval_set",
  "name": "appointment_eval_set",
  "eval_cases": [
    {
      "eval_id": "appt_happy_path",
      "conversation_scenario": {
        "starting_prompt": "Hello?",
        "conversation_plan": "When the agent offers an earlier appointment slot, say you're at work but could leave early. Accept the new time. Confirm when they say you're rescheduled. Thank them and end."
      }
    },
    {
      "eval_id": "appt_decline_last_minute",
      "conversation_scenario": {
        "starting_prompt": "Yeah?",
        "conversation_plan": "When offered the earlier slot, say it's too last minute and you'll keep your original appointment. Agent should confirm original stays and end politely."
      }
    },
    {
      "eval_id": "appt_busy",
      "conversation_scenario": {
        "starting_prompt": "Who is this?",
        "conversation_plan": "Say you can't talk right now. Agent should offer to call back. Agree and end."
      }
    },
    {
      "eval_id": "appt_billing_concern",
      "conversation_scenario": {
        "starting_prompt": "Hello?",
        "conversation_plan": "When offered the earlier slot, ask if there's a cancellation fee or if it affects your copay. Listen to the agent's response. If satisfied that there's no extra charge, accept the new slot."
      }
    },
    {
      "eval_id": "appt_change_mind",
      "conversation_scenario": {
        "starting_prompt": "Hi there",
        "conversation_plan": "Accept the earlier appointment slot initially. Then say 'Actually wait, I just realized I have a conflict. Can we keep my original time instead?' Agent should gracefully revert to original appointment."
      }
    }
  ]
}
```

---

### Task 4.2: Create Appointment Eval Config
**Goal**: `eval/eval_config_appointment.json`

Rubrics specific to scheduling:
- `clear_time_communication` — Agent clearly states available date/time
- `respects_patient_choice` — Doesn't pressure if patient declines
- `confirms_change` — Explicitly confirms the new appointment
- `sms_after_confirmation` — SMS only sent after patient confirms

Shared rubrics (reuse):
- `warm_tone`
- `concise_responses`
- `end_call_appropriate`

---

### Task 4.3: Add campaign_type to Eval Schema
**Goal**: Update `eval_schema.sql`

```sql
ALTER TABLE eval_runs ADD COLUMN IF NOT EXISTS campaign_type VARCHAR(100);
```

Update `eval_runner.py` to populate this field.

---

### Task 4.4: Update Eval Runner
**Goal**: Support running evals for specific campaigns

```bash
python -m eval.eval_runner --run --campaign hedis
python -m eval.eval_runner --run --campaign appointment
python -m eval.eval_runner --run  # Runs all
```

---

## Phase 5: Integration & Testing

### Task 5.1: End-to-End Test (HEDIS)
- [ ] Run `adk eval agents/outbound_agent metna_eval_set`
- [ ] Verify all existing scenarios pass
- [ ] Check DB results stored correctly

### Task 5.2: End-to-End Test (Appointment)
- [ ] Seed appointment mock data
- [ ] Run `adk eval agents/outbound_agent appointment_eval_set`
- [ ] Verify new scenarios work
- [ ] Check SMS tool gets called appropriately

### Task 5.3: Live Call Test
- [ ] Trigger outbound call with `campaign=appointment_backfill`
- [ ] Verify correct agent is instantiated
- [ ] Verify tools work in real conversation

---

## Dependency Graph

```
Phase 1 (Foundation)
├── Task 1.1: Folder structure
├── Task 1.2: Extract shared tools ──┐
├── Task 1.3: Extract HEDIS agent ───┼── All depend on 1.1
├── Task 1.4: Base agent class ──────┤
├── Task 1.5: Update orchestrator ───┘
└── Task 1.6: Verify (depends on 1.2-1.5)

Phase 2 (Database)
├── Task 2.1: Clinic schema (independent)
├── Task 2.2: Context loader (depends on 2.1)
└── Task 2.3: docker-compose (depends on 2.1)

Phase 3 (Appointment Agent) ─── depends on Phase 1 + Phase 2
├── Task 3.1: Appointment tools
├── Task 3.2: Golden conversations (can start in parallel)
├── Task 3.3: Appointment agent (depends on 3.1, informed by 3.2)
├── Task 3.4: Routing (depends on 3.3)
└── Task 3.5: pipe_bot update (depends on 3.4)

Phase 4 (Eval) ─── depends on Phase 3
├── Task 4.1: Eval set (informed by golden_convos)
├── Task 4.2: Eval config
├── Task 4.3: Schema update
└── Task 4.4: Runner update

Phase 5 (Testing) ─── depends on all
```

---

## Estimated Effort

| Phase | Tasks | Complexity | Estimate |
|-------|-------|------------|----------|
| 1 | 6 | Medium | 2-3 hours |
| 2 | 3 | Low | 1 hour |
| 3 | 5 | Medium | 2.5 hours |
| 4 | 4 | Low-Medium | 1.5 hours |
| 5 | 3 | Low | 1 hour |
| **Total** | **21** | | **8-9 hours** |

---

*Ready for review. Once approved, final task list goes to `execute/` folder.*
