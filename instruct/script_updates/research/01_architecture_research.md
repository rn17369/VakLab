# Research Document: Extending VakLab for Multi-Campaign Outbound Agents

## 📊 Current Architecture Overview

### Database Schema (`db-init/init.sql`)
| Table | Purpose | Key Fields |
|-------|---------|------------|
| `campaign_target_member_call_list` | Call queue for outbound calls | `member_id`, `phone_number`, `campaign_name`, `call_status` |
| `target_members_detail` | Member/patient context for personalization | `member_id`, `member_first_name`, `member_email`, `campaign_name`, `zip_code`, `csr_name` |

**Key Insight**: Data model is tightly coupled to HEDIS/mammogram use case (member-centric fields, enrollment flags).

---

### Agent Architecture (`agents/outbound_agent/`)
| File | Purpose |
|------|---------|
| `agent.py` | `MetnaAgent` (LLM agent) + `BCSGapAgent` (orchestrator) |
| `tools.py` | `send_enrollment_email`, `end_call`, `_get_member_data` |
| `__init__.py` | Exports `root_agent` |

**Current Flow**:
1. `BCSGapAgent._run_live_impl()` fetches member data via `_get_member_data()`
2. Instantiates `MetnaAgent(member_data=member_data)` with personalized instructions
3. Agent runs 4-state conversation flow (Hook → Zip Verify → Value Prop → Enrollment)

---

### Twilio Integration (`routers/outbound_twillio.py` + `routers/pipe_bot.py`)
- `/outbound-call` endpoint pulls from `campaign_target_member_call_list`
- Passes `member_id` + `campaign` to WebSocket stream
- `pipe_bot.py` uses Pipecat framework with Google STT/TTS/LLM
- Tools are registered dynamically in `run_pipe_bot()`

---

### Evaluation Framework (`eval/`)
| Component | Details |
|-----------|---------|
| `metna_eval_set.evalset.json` | 5 test scenarios (happy path, objections, decline) |
| `eval_config_stable_with_metrics.json` | Rubrics for `warm_tone`, `concise_responses`, `zip_code_verification`, tool usage |
| `eval_runner.py` | Runs ADK eval, stores results in PostgreSQL |
| `eval_schema.sql` | Tables: `eval_runs`, `eval_conversation_turns`, `eval_rubric_scores` |

---

## 🔍 Gap Analysis: HEDIS vs Appointment Backfill

| Aspect | Current (HEDIS) | Appointment Backfill (New) |
|--------|-----------------|---------------------------|
| **Goal** | Enroll in screening program | Reschedule to earlier slot |
| **Context Entity** | `target_members_detail` (member) | Need: `appointments`, `providers`, `patients` |
| **Key Data** | zip_code, email, campaign_name | appointment dates, provider, clinic name |
| **Tools** | `send_enrollment_email`, `end_call` | Need: `reschedule_appointment`, `send_sms`, `end_call` |
| **Flow States** | 4 states (Hook → Zip → Value → Enroll) | 3 states (Offer → Confirm → Update) |
| **Follow-up** | Email | SMS confirmation |

---

## 🛠️ Initial Proposed Changes

### 1. Database Additions (`db-init/`)

**New file**: `clinic_scheduler.sql`
```
Tables needed:
- clinic_info (clinic_id, name, address, phone)
- providers (provider_id, clinic_id, name, specialty)  
- patients (patient_id, phone_number, first_name, email)
- appointments (appt_id, patient_id, provider_id, date, time, status)
- appointment_backfill_queue (like campaign_target_member_call_list but for scheduling)
```

### 2. Agent Structure Options

**Option A**: Per-campaign agent folders (INITIAL PROPOSAL)
```
agents/
├── outbound_agent/          # Keep existing (HEDIS)
├── appointment_agent/       # New folder
└── shared/                  # Extract common patterns
```

### 3. Eval Framework Updates

**New files needed**:
- New eval set for appointment scenarios
- New rubrics specific to scheduling

---

*See `02_opportunities_and_risks.md` for deeper analysis*
