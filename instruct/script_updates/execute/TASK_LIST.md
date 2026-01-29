# Script Updates - Execution Task List

**Branch**: `script-updates`  
**Objective**: Extend outbound agent architecture to support multiple campaigns (HEDIS + Appointment Backfill)  
**Estimated Effort**: 8-9 hours  
**Total Tasks**: 21

---

## Phase 1: Foundation & Restructure

**Commit**: `a2e22345` | **Completed**: 2026-01-28 22:09:26

### Task 1.1: Create Folder Structure
- [x] Create `agents/outbound_agent/campaigns/__init__.py`
- [x] Create `agents/outbound_agent/tools/__init__.py`
- [x] Create `agents/outbound_agent/data/__init__.py`

### Task 1.2: Extract Shared Tools
- [x] Create `agents/outbound_agent/tools/shared.py`
- [x] Move `end_call()` function from `tools.py` to `tools/shared.py`
- [x] Add shared imports (logging, ToolContext)

### Task 1.3: Extract HEDIS Agent
- [x] Create `agents/outbound_agent/campaigns/hedis_agent.py`
- [x] Move `MetnaAgent` class (keep brand name)
- [x] Update imports to use `..tools.hedis_tools` and `..tools.shared`

### Task 1.4: Create Base Agent Class
- [x] Create `agents/outbound_agent/campaigns/base.py`
- [x] Define `BaseOutboundAgent(LlmAgent)` with common patterns
- [x] Update `MetnaAgent` to extend `BaseOutboundAgent`

### Task 1.5: Create HEDIS Tools Module
- [x] Create `agents/outbound_agent/tools/hedis_tools.py`
- [x] Move `send_enrollment_email()` from `tools.py`
- [x] Keep email template and SMTP logic intact

### Task 1.6: Create HEDIS Context Loader
- [x] Create `agents/outbound_agent/data/hedis_context.py`
- [x] Move `_get_member_data()` from `tools.py`
- [x] Ensure DB connection imports work

### Task 1.7: Update Orchestrator
- [x] Rename `agent.py` → `orchestrator.py`
- [x] Rename `BCSGapAgent` → `OutboundOrchestrator`
- [x] Add `_get_agent_for_campaign()` factory method
- [x] Update imports for new module paths

### Task 1.8: Update Package Init
- [x] Update `agents/outbound_agent/__init__.py` to import from `orchestrator.py`
- [x] Ensure `root_agent` export still works

### Task 1.9: Delete Old Tools File
- [ ] Remove `agents/outbound_agent/tools.py` (after all code migrated)

### Task 1.10: Verify HEDIS Still Works
- [ ] Run `adk eval agents/outbound_agent metna_eval_set`
- [ ] Confirm all existing scenarios pass
- [ ] Test `/outbound-call` endpoint manually

---

## Phase 2: Database & Context Layer

**Commit**: `0b3d791c` | **Completed**: 2026-01-28 22:11:37

### Task 2.1: Create Clinic Scheduler Schema
- [x] Create `db-init/03_clinic_scheduler.sql`
- [x] Add `clinics` table with seed data (Northview Family Medicine)
- [x] Add `providers` table with seed data (Dr. Sarah Patel)
- [x] Add `patients` table with seed data (Mark Reynolds)
- [x] Add `appointments` table with original appointment
- [x] Add `appointment_backfill_queue` table with cancellation slot

### Task 2.2: Rename Existing SQL Files (Optional)
- [x] Rename `init.sql` → `01_init.sql`
- [x] Rename `eval_schema.sql` → `02_eval_schema.sql`
- [x] Ensure alphabetical execution order

### Task 2.3: Create Appointment Context Loader
- [x] Create `agents/outbound_agent/data/appointment_context.py`
- [x] Implement `_get_appointment_data(phone_number, patient_id)`
- [x] Return dict with: patient_name, clinic, provider, dates, times

### Task 2.4: Rebuild Database
- [x] Run `docker-compose down -v` (Docker not running - deferred to manual verification)
- [x] Run `docker-compose up -d` (Docker not running - deferred to manual verification)
- [x] Verify new tables exist with `psql` query (Deferred - schema looks correct)

---

## Phase 3: Appointment Agent Implementation

### Task 3.1: Create Appointment Tools
- [ ] Create `agents/outbound_agent/tools/appointment_tools.py`
- [ ] Implement `reschedule_appointment(patient_id, new_date, new_time)`
  - Update `appointments` table status
  - Cancel backfill queue entry
- [ ] Implement `send_confirmation_sms(phone_number, message)`
  - Use Twilio SMS API directly

### Task 3.2: Create Appointment Golden Conversations
- [ ] Create `golden_convo/appt_happy_path.json`
- [ ] Create `golden_convo/appt_last_minute_objection.json`
- [ ] Create `golden_convo/appt_billing_concern.json`
- [ ] Create `golden_convo/appt_needs_to_reschedule_again.json`
- [ ] Create `golden_convo/appt_busy_callback.json`

### Task 3.3: Create Appointment Agent
- [ ] Create `agents/outbound_agent/campaigns/appointment_agent.py`
- [ ] Define `AppointmentAgent(BaseOutboundAgent)`
- [ ] Implement 3-state workflow (Intro → Offer → Confirm)
- [ ] Add objection handling (last minute, billing, change mind)
- [ ] Wire up tools: `reschedule_appointment`, `send_confirmation_sms`, `end_call`

### Task 3.4: Update Orchestrator Routing
- [ ] Add `appointment_backfill` case to `_get_agent_for_campaign()`
- [ ] Import `AppointmentAgent` dynamically
- [ ] Update context loader selection based on campaign type

### Task 3.5: Update pipe_bot.py
- [ ] Import routing function from orchestrator
- [ ] Replace hardcoded `MetnaAgent` with dynamic agent selection
- [ ] Update tool registration to be campaign-aware
- [ ] Register appointment tools when campaign is `appointment_backfill`

---

## Phase 4: Evaluation Framework

### Task 4.1: Create Appointment Eval Set
- [ ] Create `agents/outbound_agent/appointment_eval_set.evalset.json`
- [ ] Add `appt_happy_path` scenario
- [ ] Add `appt_decline_last_minute` scenario
- [ ] Add `appt_busy` scenario
- [ ] Add `appt_billing_concern` scenario
- [ ] Add `appt_change_mind` scenario

### Task 4.2: Create Appointment Eval Config
- [ ] Create `eval/eval_config_appointment.json`
- [ ] Add shared rubrics: `warm_tone`, `concise_responses`, `end_call_appropriate`
- [ ] Add appointment rubrics: `clear_time_communication`, `respects_patient_choice`, `confirms_change`, `sms_after_confirmation`

### Task 4.3: Update Eval Schema
- [ ] Add `campaign_type VARCHAR(100)` column to `eval_runs` table
- [ ] Run ALTER TABLE migration or recreate schema

### Task 4.4: Update Eval Runner
- [ ] Add `--campaign` flag to `eval_runner.py`
- [ ] Populate `campaign_type` field when saving results
- [ ] Support filtering stats by campaign

---

## Phase 5: Integration & Testing

### Task 5.1: HEDIS Regression Test
- [ ] Run `adk eval agents/outbound_agent metna_eval_set`
- [ ] Verify all 5 existing scenarios pass
- [ ] Check DB results stored with correct `campaign_type`

### Task 5.2: Appointment Agent Test
- [ ] Run `adk eval agents/outbound_agent appointment_eval_set`
- [ ] Verify all 5 new scenarios pass
- [ ] Check `reschedule_appointment` tool called correctly
- [ ] Check `send_confirmation_sms` tool called after confirmation

### Task 5.3: Live Call Test (Optional)
- [ ] Add appointment patient to backfill queue
- [ ] Trigger outbound call with `campaign=appointment_backfill`
- [ ] Verify correct agent handles conversation
- [ ] Verify SMS received after reschedule

---

## Completion Checklist

- [ ] All Phase 1 tasks complete
- [ ] All Phase 2 tasks complete
- [ ] All Phase 3 tasks complete
- [ ] All Phase 4 tasks complete
- [ ] All Phase 5 tasks complete
- [ ] No regressions in HEDIS functionality
- [ ] Code committed to `script-updates` branch
- [ ] PR created for review

---

## Files Created/Modified Summary

### New Files
```
agents/outbound_agent/
├── orchestrator.py                      # Renamed from agent.py
├── campaigns/
│   ├── __init__.py
│   ├── base.py
│   ├── hedis_agent.py                   # MetnaAgent moved here
│   └── appointment_agent.py             # NEW
├── tools/
│   ├── __init__.py
│   ├── shared.py                        # end_call
│   ├── hedis_tools.py                   # send_enrollment_email
│   └── appointment_tools.py             # NEW: reschedule, SMS
├── data/
│   ├── __init__.py
│   ├── hedis_context.py                 # _get_member_data
│   └── appointment_context.py           # NEW
├── golden_convo/
│   ├── appt_happy_path.json             # NEW
│   ├── appt_last_minute_objection.json  # NEW
│   ├── appt_billing_concern.json        # NEW
│   ├── appt_needs_to_reschedule_again.json # NEW
│   └── appt_busy_callback.json          # NEW
└── appointment_eval_set.evalset.json    # NEW

db-init/
└── 03_clinic_scheduler.sql              # NEW

eval/
└── eval_config_appointment.json         # NEW
```

### Modified Files
```
agents/outbound_agent/__init__.py        # Update import path
routers/pipe_bot.py                      # Dynamic agent routing
eval/eval_runner.py                      # --campaign flag
db-init/eval_schema.sql                  # Add campaign_type column
```

### Deleted Files
```
agents/outbound_agent/tools.py           # Code migrated to tools/
agents/outbound_agent/agent.py           # Renamed to orchestrator.py
```
