# VakLab Gap Analysis Report

> **Target Vision Reference:** VekLabs Pitch Deck - "The Control Plane for Healthcare Outreach"  
> **Assessment Date:** January 29, 2026  
> **Codebase Branch:** `script-updates`

---

## Executive Summary

This document identifies gaps between VakLab's current implementation and the vision outlined in the pitch deck. Each gap is categorized by:
- **Risk Level:** Critical | High | Medium | Low
- **Gap Type:** Compliance | Security | Reliability | Scalability | Feature | Technical Debt
- **Effort to Close:** S (days) | M (weeks) | L (months)

---

## 1. Compliance & Trust Gaps

### 1.1 🔴 CRITICAL: No HIPAA-Compliant Audit Logging

**Current State:**  
- Basic `logging.info()` and `logger.info()` calls scattered throughout codebase
- No structured audit trail for call events
- PII (names, emails, phone numbers) flows through logs without redaction

**Evidence in Code:**
```python
# hedis_context.py - Raw PII returned and likely logged
return {
    "member_id": member_id,
    "member_first_name": member_first_name,
    "member_email": member_email,
    ...
}

# pipe_bot.py - Direct logging of context data
logger.info(f"Context data loaded: {context_data}")
```

**Why It's a Risk:**
- **Pitch Deck Claim:** "Encrypt data - Vak agent never sees PII"
- **Reality:** PII flows openly through application logs
- **Consequence:** HIPAA violation, failed BAA audits, enterprise deal blockers

**Remediation:**
1. Implement structured logging with PII redaction layer
2. Add OpenTelemetry traces with attribute sanitization
3. Store audit logs in HIPAA-compliant sink (BigQuery with access controls, or dedicated HIPAA logging service)
4. Add call recording consent tracking

**Effort:** L (4-6 weeks for production-grade implementation)

---

### 1.2 🔴 CRITICAL: Twilio Signature Validation Bypassed

**Current State:**  
```python
# security.py - Validation completely skipped in development
if "localhost" in domain or "127.0.0.1" in domain or "ngrok" in domain:
    return  # Allow requests in development mode
```

**Why It's a Risk:**
- Any ngrok URL bypasses webhook validation
- Production deployment would need complete rewrite
- Opens door for spoofed webhooks

**Pitch Deck Claim:** "Records and audits all interactions for review"  
**Reality:** No verification that calls originate from Twilio

**Remediation:**
1. Implement proper Twilio signature validation in all environments
2. Add unit tests for webhook validation
3. Use environment variable `ENVIRONMENT=production` to control strict mode

**Effort:** S (2-3 days)

---

### 1.3 🟡 HIGH: No Call Recording or Consent Management

**Current State:**  
- No call recording integration
- No consent language in agent scripts
- No "this call may be recorded" disclosure

**Why It's a Risk:**
- Healthcare outreach legally requires consent disclosures in many states
- No ability to audit what was actually said on calls
- Can't defend against complaints without recordings

**Remediation:**
1. Add Twilio call recording with consent prompt
2. Store recordings in HIPAA-compliant storage
3. Add consent tracking to database schema
4. Update agent prompts with required disclosures

**Effort:** M (1-2 weeks)

---

## 2. Reliability & Production Readiness Gaps

### 2.1 🔴 CRITICAL: No Error Recovery in Call Flow

**Current State:**  
```python
# pipe_bot.py - Single try/except with full failure
try:
    # All pipeline setup
except Exception as ex:
    logger.error(f"ERROR in run_pipe_bot: {ex}", exc_info=True)
    raise
```

**Why It's a Risk:**
- **Pitch Deck Claim:** "Escalates to human when necessary"
- **Reality:** Any exception kills the call - no graceful handoff
- Patient hears dead air or disconnect on any error
- No retry logic for transient failures (Google API, database)

**Evidence of Missing Patterns:**
- No circuit breaker for Google services
- No fallback if STT/TTS fails
- No warm handoff to human agent on error

**Remediation:**
1. Implement graceful degradation ("I'm having trouble, let me transfer you")
2. Add circuit breaker pattern for external services
3. Build human handoff capability (transfer to conference line)
4. Add retry with exponential backoff for transient failures

**Effort:** L (3-4 weeks)

---

### 2.2 🔴 CRITICAL: Hardcoded Credentials Path

**Current State:**  
```python
# pipe_bot.py - Absolute path to credentials
stt = GoogleSTTService(
    credentials_path="/Users/rn/Documents/gcp_hackthon/cool-furnace-483603-b2-fdd4814415cb.json",
    ...
)
```

**Why It's a Risk:**
- Will break on any other machine
- Credentials file checked into path references
- Not deployable to cloud without complete rewrite

**Remediation:**
1. Use `GOOGLE_APPLICATION_CREDENTIALS` environment variable
2. In production, use workload identity or secret manager
3. Remove all hardcoded paths from codebase

**Effort:** S (1 day)

---

### 2.3 🟡 HIGH: No Distributed Tracing

**Current State:**  
- No OpenTelemetry integration
- No correlation IDs across call lifecycle
- Can't trace a call from Twilio → Pipecat → LLM → Tools → Database

**Why It's a Risk:**
- **Pitch Deck Claim:** "Institutional Learning That Compounds Over Time"
- **Reality:** No way to correlate call outcomes with system behavior
- Can't diagnose production issues without tracing
- No performance metrics (latency per stage)

**Remediation:**
1. Add OpenTelemetry SDK to FastAPI
2. Propagate trace context through Pipecat pipeline
3. Instrument LLM calls, tool executions, database queries
4. Export to Google Cloud Trace or Jaeger

**Effort:** M (2 weeks)

---

### 2.4 🟡 HIGH: No State Persistence for Call Recovery

**Current State:**  
```python
# orchestrator.py - State lives only in session
ctx.session.state["call_ended"] = True
```

**Why It's a Risk:**
- If process crashes mid-call, all state is lost
- Can't resume or analyze incomplete calls
- No way to track call progress across restarts

**Remediation:**
1. Add Redis or DynamoDB for durable call state
2. Checkpoint state at each conversation turn
3. Build call recovery mechanism

**Effort:** M (2 weeks)

---

## 3. Security Gaps

### 3.1 🔴 CRITICAL: Database Credentials in Environment Variables

**Current State:**  
```python
# db.py - Plain text credentials from environment
DB_PASS = os.environ.get("DB_PASSWORD", "password")
```

**Why It's a Risk:**
- Default password is "password"
- No secrets management integration
- Environment variables visible in process listings

**Remediation:**
1. Integrate with Google Secret Manager or HashiCorp Vault
2. Remove default credentials
3. Add secret rotation capability

**Effort:** M (1 week)

---

### 3.2 🟡 HIGH: No Input Validation on Tool Parameters

**Current State:**  
```python
# appointment_tools.py - SQL injection potential
cur.execute("""
    UPDATE appointments
    SET appointment_date = %s, appointment_time = %s, status = 'rescheduled'
    WHERE patient_id = %s
    ...
""", (new_date, new_time, patient_id))
```

**Analysis:**
- Uses parameterized queries (good!)
- But no validation that `new_date` is a valid date format
- LLM could hallucinate invalid data

**Remediation:**
1. Add Pydantic validation to all tool parameters
2. Validate date/time formats before database calls
3. Add allowlist for status values

**Effort:** S (2-3 days)

---

### 3.3 🟢 MEDIUM: CORS Allows All Origins

**Current State:**  
```python
# main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    ...
)
```

**Why It's a Risk:**
- Acceptable for development
- Production should restrict to known domains

**Remediation:**
1. Configure allowed origins via environment variable
2. Different settings for dev/staging/production

**Effort:** S (1 day)

---

## 4. Scalability Gaps

### 4.1 🟡 HIGH: Single Database Connection Per Request

**Current State:**  
```python
# db.py - New connection every call
def get_db_connection():
    conn = psycopg2.connect(...)
    return conn
```

**Why It's a Risk:**
- Connection overhead on every operation
- Will exhaust connections under load
- No connection pooling

**Remediation:**
1. Implement connection pooling (psycopg2.pool or SQLAlchemy)
2. Add connection health checks
3. Configure pool size based on expected concurrent calls

**Effort:** S (2-3 days)

---

### 4.2 🟡 HIGH: No Rate Limiting

**Current State:**  
- No rate limiting on any endpoints
- `/twilio/outbound-call` can be spammed

**Why It's a Risk:**
- DoS vulnerability
- Could trigger massive Twilio bills
- No protection against runaway automation

**Remediation:**
1. Add rate limiting middleware (slowapi or custom)
2. Implement per-phone-number call throttling
3. Add daily/hourly campaign limits

**Effort:** S (2-3 days)

---

### 4.3 🟢 MEDIUM: No Horizontal Scaling Design

**Current State:**  
- Single-instance design assumed
- No distributed locking for call queue
- `campaign_target_member_call_list` has no row-level locking

**Why It's a Risk:**
- **Pitch Deck Claim:** "Coverage & Throughput Without Organizational Drag"
- **Reality:** Can only run one instance without duplicate calls
- Linear scaling only

**Remediation:**
1. Add `SELECT FOR UPDATE SKIP LOCKED` for call queue
2. Design for stateless workers with shared Redis
3. Document horizontal scaling architecture

**Effort:** M (2-3 weeks)

---

## 5. Feature Gaps (Relative to Pitch Deck)

### 5.1 🟡 HIGH: No Inbound Call Support

**Pitch Deck Claim:** "VakLabs Solution (Inbound)" slide shows:
- Appointment Scheduling/Reschedule
- Billing Questions
- Prescription Filling

**Current State:**  
- Only outbound calling implemented
- No IVR or inbound routing

**Remediation:**
1. Design inbound call router
2. Implement intent detection for routing
3. Build additional campaign types (billing, Rx)

**Effort:** L (6-8 weeks per campaign)

---

### 5.2 🟡 HIGH: Missing Campaign Types

**Pitch Deck Claims:**
- Billing Collection Reminders ❌
- Prescription Reminders ❌
- CAHPS Survey Engagement ❌
- Discharge Procedure Adherence ❌

**Current State:**  
- Only HEDIS and Appointment Backfill implemented

**Remediation:**
1. Design campaign template system
2. Implement each campaign with proper tools
3. Add campaign-specific eval sets

**Effort:** L (2-4 weeks per campaign)

---

### 5.3 🟢 MEDIUM: No Multi-Tenant Support

**Pitch Deck Claim:** "Campaigns run independently. Intelligence compounds centrally."

**Current State:**  
- Single-tenant database schema
- No clinic/organization isolation
- No per-tenant configuration

**Remediation:**
1. Add `organization_id` to all tables
2. Implement tenant isolation in queries
3. Build admin UI for tenant management

**Effort:** L (4-6 weeks)

---

## 6. Testing & Quality Gaps

### 6.1 🔴 CRITICAL: Minimal Test Coverage

**Current State:**  
- `test_outbound.py` - Only tests API endpoint responds
- No unit tests for tools
- No integration tests for call flow
- No mocking of external services

**Evidence:**
```python
# test_outbound.py - Just hits endpoints
response = requests.post(OUTBOUND_ENDPOINT, timeout=10)
```

**Why It's a Risk:**
- Can't refactor safely
- Regressions will go unnoticed
- No CI/CD quality gates

**Remediation:**
1. Add unit tests for all tools (mock database)
2. Add integration tests for orchestrator (mock LLM)
3. Add contract tests for Twilio webhooks
4. Implement CI pipeline with test gates

**Effort:** L (ongoing, 4-6 weeks initial)

---

### 6.2 🟢 MEDIUM: Eval Framework is Strong but Incomplete

**Current State:**  
- Good: Eval sets exist for both campaigns
- Good: Rubric-based evaluation with hallucination/safety checks
- Gap: No automated regression testing
- Gap: No eval result trending/alerting

**Remediation:**
1. Add eval run to CI pipeline
2. Build alerting when scores drop below thresholds
3. Track eval scores over time for trends

**Effort:** M (1-2 weeks)

---

## 7. Technical Debt

### 7.1 🟡 HIGH: sys.path Manipulation

**Current State:**  
```python
# hedis_context.py, appointment_context.py - Brittle imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
```

**Why It's a Risk:**
- Breaks with different working directories
- Makes testing difficult
- Will fail in containerized deployments

**Remediation:**
1. Convert to proper Python package with `pyproject.toml`
2. Use relative imports within package
3. Install package in editable mode for development

**Effort:** M (1 week)

---

### 7.2 🟢 MEDIUM: Duplicate Tool Definitions

**Current State:**  
Tools are defined twice:
1. As Python functions in `tools/*.py`
2. As JSON schemas in `pipe_bot.py`

**Why It's a Risk:**
- Easy for definitions to drift
- Maintenance burden

**Remediation:**
1. Generate JSON schemas from function signatures
2. Use single source of truth for tool definitions
3. Consider using Pydantic models for tool parameters

**Effort:** M (1 week)

---

## Summary: Priority Remediation Roadmap

### Phase 1: Production Blockers (Weeks 1-3)
| Gap | Effort | Priority |
|-----|--------|----------|
| 2.2 Hardcoded Credentials | S | MUST |
| 1.2 Twilio Validation | S | MUST |
| 3.1 Secret Management | M | MUST |
| 4.1 Connection Pooling | S | SHOULD |
| 4.2 Rate Limiting | S | SHOULD |

### Phase 2: Compliance & Trust (Weeks 4-8)
| Gap | Effort | Priority |
|-----|--------|----------|
| 1.1 HIPAA Audit Logging | L | MUST for enterprise |
| 1.3 Call Recording | M | MUST for compliance |
| 2.3 Distributed Tracing | M | SHOULD |

### Phase 3: Reliability & Scale (Weeks 9-14)
| Gap | Effort | Priority |
|-----|--------|----------|
| 2.1 Error Recovery | L | MUST for production |
| 2.4 State Persistence | M | SHOULD |
| 4.3 Horizontal Scaling | M | SHOULD |

### Phase 4: Feature Expansion (Weeks 15+)
| Gap | Effort | Priority |
|-----|--------|----------|
| 5.1 Inbound Calls | L | Roadmap |
| 5.2 New Campaigns | L | Roadmap |
| 5.3 Multi-Tenant | L | Roadmap |

---

## Conclusion

VakLab has a **solid architectural foundation** with good patterns (orchestrator routing, campaign modularity, eval framework). However, there's a significant gap between the pitch deck claims and production reality.

**Strengths to Build On:**
- Clean campaign abstraction
- Evaluation infrastructure ahead of competitors
- Good use of Google ADK/Pipecat stack

**Critical Actions Before Enterprise Sales:**
1. Fix credential management
2. Implement HIPAA-compliant logging
3. Add Twilio validation
4. Build human handoff capability
5. Establish test coverage

The technical debt is manageable if addressed systematically. The architecture doesn't need a rewrite—it needs hardening.
