# Pitch Deck Claims vs. Codebase Reality

> **Purpose:** Direct mapping of VekLabs Pitch Deck claims to current implementation status  
> **Assessment Date:** January 29, 2026

---

## Claim Verification Matrix

### Slide: "Safety, Trust, and Control"

| Claim | Status | Evidence | Gap |
|-------|--------|----------|-----|
| **"Does NOT give 'Over the Phone' Diagnosis"** | ✅ TRUE | Agent prompts focus on scheduling/enrollment, not medical advice | None |
| **"Does NOT give medical advice"** | ✅ TRUE | HEDIS agent discusses screening logistics, not diagnosis | None |
| **"Does NOT Mishandle HIPPA"** | ⚠️ UNVERIFIED | No HIPAA logging, PII in logs, no BAA infrastructure | Critical gap |
| **"Does NOT Drift or hallucinate"** | ⚠️ PARTIAL | Eval framework tests for hallucinations, but no production guardrails | Medium gap |
| **"Escalates to human when necessary"** | ❌ NOT IMPLEMENTED | No human handoff capability in codebase | Critical gap |
| **"Integrate with existing infrastructure"** | ⚠️ PARTIAL | PostgreSQL integration exists, no EHR/EMR connectors | Feature gap |
| **"Records and audits all interactions"** | ❌ NOT IMPLEMENTED | No call recording, basic logging only | Critical gap |
| **"Encrypt data - Vak agent never sees PII"** | ❌ FALSE | PII flows through agent context, logged unencrypted | Critical gap |

### Slide: "Why Vak is Different" - System Guarantees

| Claim | Status | Evidence | Gap |
|-------|--------|----------|-----|
| **"Intent is understood and validated"** | ⚠️ PARTIAL | LLM handles intent, no explicit validation layer | Low priority |
| **"Information and data are secure and verified during the call"** | ❌ FALSE | No data verification, no encryption in transit within app | High gap |
| **"Conversations operate within defined guardrails"** | ⚠️ PARTIAL | Prompt engineering only, no runtime guardrails | Medium gap |

### Slide: "Why Clinics Care" - Pillars

| Pillar | Claim | Status | Evidence |
|--------|-------|--------|----------|
| **Pillar 1** | "Outcome Reliability: Not automation, autonomy" | ⚠️ PARTIAL | Good eval framework, but no production monitoring |
| **Pillar 2** | "Coverage & Throughput Without Organizational Drag" | ⚠️ LIMITED | Single-instance only, no horizontal scaling |
| **Pillar 3** | "Human Leverage, Not Human Replacement" | ❌ NOT IMPLEMENTED | No human-in-the-loop capability |
| **Pillar 4** | "Institutional Learning That Compounds Over Time" | ⚠️ PARTIAL | Eval history stored, but no feedback loop to training |

---

## Feature Claims vs. Implementation

### Outbound Capabilities (Slide 04a)

| Feature | Claimed | Implemented | Notes |
|---------|---------|-------------|-------|
| Appointment Reminders | ✅ | ✅ | AppointmentAgent exists |
| Billing Collection Reminders | ✅ | ❌ | Not implemented |
| Prescription Reminders | ✅ | ❌ | Not implemented |
| Early Appointment Entry | ✅ | ⚠️ | Backfill only, not proactive |
| CAHPS Survey Engagement | ✅ | ❌ | Not implemented |
| Discharge Procedure Adherence | ✅ | ❌ | Not implemented |

**Coverage:** 2/6 claimed features implemented (33%)

### Inbound Capabilities (Slide 04b)

| Feature | Claimed | Implemented | Notes |
|---------|---------|-------------|-------|
| Records Check | ✅ | ❌ | No inbound support |
| Appointment Scheduling | ✅ | ❌ | Outbound only |
| Billing Questions | ✅ | ❌ | Not implemented |
| Prescription Filling | ✅ | ❌ | Not implemented |
| Human Agent Transfer | ✅ | ❌ | Not implemented |

**Coverage:** 0/5 claimed features implemented (0%)

---

## Technology Claims

### "Tech Stack" (README.md matches Pitch)

| Component | Claimed | Implemented | Version/Notes |
|-----------|---------|-------------|---------------|
| Google Gemini | ✅ | ✅ | gemini-2.5-flash in agents, gemini-3-flash-preview in pipe_bot |
| Google ADK | ✅ | ✅ | Used for agent framework |
| Google Cloud STT | ✅ | ✅ | GoogleSTTService in pipeline |
| Google Cloud TTS | ✅ | ✅ | Journey-F voice configured |
| Pipecat AI | ✅ | ✅ | Full pipeline implementation |
| Twilio Voice | ✅ | ✅ | Outbound calling works |
| PostgreSQL | ✅ | ✅ | Docker compose setup |

**Tech Stack Accuracy:** 100% - Claims match implementation

---

## Business Model Alignment

### "Enabler" vs "Operator" Model

| Aspect | Enabler Model | Operator Model | Current State |
|--------|---------------|----------------|---------------|
| Execution | Customer Directed | Vak Owned | Vak Owned ✅ |
| Time to Value | Learn → then Value | Immediate | Requires setup (gap) |
| Learning Model | Cross-Customer | Isolated | Single-tenant (gap) |
| Multi-tenant | Required | Not Required | ❌ Not implemented |

**Assessment:** Current architecture supports "Operator" model only. "Enabler" model requires significant multi-tenancy work.

---

## Risk Assessment by Audience

### For Technical Due Diligence (Enterprise Buyer)

| Risk Area | Severity | Finding |
|-----------|----------|---------|
| HIPAA Compliance | 🔴 CRITICAL | No audit logging, PII exposure |
| Security | 🔴 CRITICAL | Hardcoded credentials, weak validation |
| Reliability | 🟡 HIGH | No error recovery, no human handoff |
| Scalability | 🟡 HIGH | Single-instance design |
| Test Coverage | 🟡 HIGH | Minimal tests |

### For Investor Due Diligence

| Concern | Severity | Finding |
|---------|----------|---------|
| Feature Claims | 🟡 MEDIUM | 33% outbound, 0% inbound implemented |
| Tech Claims | 🟢 LOW | Stack is accurate |
| Compliance Claims | 🔴 HIGH | Significant gap |
| Scalability Claims | 🟡 MEDIUM | Architecture is sound, implementation needs work |

---

## Recommendations

### Before Enterprise Demos
1. ❌ Do not claim "Vak agent never sees PII" - this is provably false
2. ❌ Do not claim "Records and audits all interactions" - not implemented
3. ✅ Can claim strong AI foundation and eval framework
4. ✅ Can demonstrate working HEDIS and Appointment campaigns

### Messaging Adjustments
| Current Claim | Suggested Revision |
|---------------|-------------------|
| "Encrypt data - Vak agent never sees PII" | "Designed for HIPAA compliance with configurable PII handling" |
| "Escalates to human when necessary" | "Roadmap includes seamless human handoff" |
| "Records and audits all interactions" | "Built for auditability with structured logging" |

### Quick Wins for Credibility
1. **Fix credentials hardcoding** - 1 day effort, removes obvious red flag
2. **Implement Twilio validation** - 2 days, shows security awareness
3. **Add basic call event logging to DB** - 3 days, enables "audit trail" claim

---

## Conclusion

The pitch deck presents a **vision** that is partially implemented. The core technology claims are accurate, but the compliance and safety claims have significant gaps. 

**Honest positioning:** VakLab is a strong MVP/prototype with proven technology that requires production hardening before enterprise deployment.

**Not recommended:** Presenting current state as enterprise-ready to healthcare buyers who will conduct technical due diligence.
