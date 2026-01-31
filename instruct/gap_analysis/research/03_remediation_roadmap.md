# VakLab Remediation Roadmap

> **Purpose:** Actionable tasks to close gaps between current state and pitch deck vision  
> **Timeline:** 14-week phased approach  
> **Reference:** 01_gap_analysis_comprehensive.md, 02_pitch_deck_truth_table.md

---

## Phase 1: Production Blockers (Weeks 1-2)

**Goal:** Remove obvious technical debt that would fail any technical review

### Task 1.1: Fix Hardcoded Credentials
**File:** `routers/pipe_bot.py`  
**Current:**
```python
credentials_path="/Users/rn/Documents/gcp_hackthon/cool-furnace-483603-b2-fdd4814415cb.json"
```
**Action:**
1. Replace with `os.getenv("GOOGLE_APPLICATION_CREDENTIALS")`
2. Update `.env.example` with documentation
3. Add validation on startup if credentials missing

**Effort:** 2 hours  
**Owner:** ___________

---

### Task 1.2: Implement Twilio Webhook Validation
**File:** `utils/security.py`  
**Current:** Validation skipped for all ngrok URLs  
**Action:**
1. Add `ENVIRONMENT` env var (development/staging/production)
2. Only skip validation in `development` environment
3. Add proper signature validation for staging/production
4. Add unit tests for validation logic

**Effort:** 1 day  
**Owner:** ___________

---

### Task 1.3: Add Secret Management
**Files:** `utils/db.py`, `routers/pipe_bot.py`, `agents/outbound_agent/tools/*.py`  
**Action:**
1. Create `utils/secrets.py` wrapper for Google Secret Manager
2. Replace all `os.getenv()` calls for sensitive values
3. Add local fallback for development (dotenv)
4. Document secret names in README

**Effort:** 3 days  
**Owner:** ___________

---

### Task 1.4: Implement Connection Pooling
**File:** `utils/db.py`  
**Current:** New connection per request  
**Action:**
```python
# New implementation
from psycopg2 import pool

connection_pool = pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=20,
    host=DB_HOST,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASS
)

def get_db_connection():
    return connection_pool.getconn()

def release_connection(conn):
    connection_pool.putconn(conn)
```

**Effort:** 1 day  
**Owner:** ___________

---

### Task 1.5: Add Rate Limiting
**File:** `main.py`, new `utils/rate_limit.py`  
**Action:**
1. Add `slowapi` to requirements.txt
2. Implement rate limiting middleware
3. Configure limits:
   - `/twilio/outbound-call`: 10 requests/minute
   - `/api/eval/*`: 100 requests/minute
4. Add per-phone-number call throttling

**Effort:** 2 days  
**Owner:** ___________

---

## Phase 2: Compliance Foundation (Weeks 3-5)

**Goal:** Enable truthful "built for compliance" claims

### Task 2.1: Structured Audit Logging
**New Files:** `utils/audit.py`, `db-init/04_audit_schema.sql`  
**Action:**
1. Create `call_events` table schema:
```sql
CREATE TABLE call_events (
    id SERIAL PRIMARY KEY,
    call_sid VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL,  -- call_started, tool_invoked, call_ended
    event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_data JSONB,  -- Sanitized, no raw PII
    campaign_type VARCHAR(50),
    member_id_hash VARCHAR(64),  -- SHA256 of member_id
    trace_id VARCHAR(100)
);
```

2. Create audit logger with PII redaction:
```python
def log_call_event(call_sid, event_type, data):
    sanitized = redact_pii(data)
    # Store to database
```

3. Add audit points in:
   - `orchestrator.py` - call start/end
   - `pipe_bot.py` - tool invocations
   - All tool functions - action results

**Effort:** 5 days  
**Owner:** ___________

---

### Task 2.2: PII Redaction Layer
**New File:** `utils/pii.py`  
**Action:**
1. Implement redaction functions:
```python
PII_PATTERNS = {
    'email': r'[\w\.-]+@[\w\.-]+\.\w+',
    'phone': r'\+?1?\d{10,}',
    'ssn': r'\d{3}-\d{2}-\d{4}',
}

def redact_pii(data: dict) -> dict:
    """Replace PII with [REDACTED] markers"""
    
def hash_pii(value: str, salt: str) -> str:
    """One-way hash for correlation without exposure"""
```

2. Wrap all logging calls through redaction
3. Add `@redact_logs` decorator for functions

**Effort:** 3 days  
**Owner:** ___________

---

### Task 2.3: Call Recording Integration
**File:** `routers/outbound_twillio.py`  
**Action:**
1. Add `Record="true"` to TwiML
2. Store recording SID in call_events
3. Add consent disclosure to agent prompts
4. Create recording retrieval API (for compliance reviews)

**Effort:** 3 days  
**Owner:** ___________

---

### Task 2.4: Consent Tracking
**Files:** `db-init/05_consent_schema.sql`, agent prompts  
**Action:**
1. Add consent tracking table:
```sql
CREATE TABLE consent_records (
    id SERIAL PRIMARY KEY,
    call_sid VARCHAR(100),
    consent_type VARCHAR(50),  -- recording, hipaa_disclosure
    consent_given BOOLEAN,
    consent_timestamp TIMESTAMP
);
```

2. Update agent prompts with disclosure language
3. Log consent events

**Effort:** 2 days  
**Owner:** ___________

---

## Phase 3: Reliability (Weeks 6-8)

**Goal:** Production-ready error handling and recovery

### Task 3.1: Graceful Error Recovery
**File:** `routers/pipe_bot.py`  
**Action:**
1. Wrap pipeline stages in try/except with fallbacks:
```python
try:
    # STT processing
except STTError:
    await say_fallback("I'm having trouble hearing you. Let me transfer you to an agent.")
    await transfer_to_human()
```

2. Add fallback TTS messages for common errors
3. Implement circuit breaker for Google services

**Effort:** 5 days  
**Owner:** ___________

---

### Task 3.2: Human Handoff Capability
**Files:** `routers/pipe_bot.py`, `utils/twilio_helpers.py`  
**Action:**
1. Create conference-based handoff:
```python
async def transfer_to_human(call_sid, reason):
    # 1. Create conference
    # 2. Add current call to conference
    # 3. Dial human agent into conference
    # 4. AI agent leaves
```

2. Add CSR phone number lookup from database
3. Trigger handoff on:
   - Explicit request ("talk to a person")
   - Error conditions
   - Conversation loops (detected by turn count)

**Effort:** 5 days  
**Owner:** ___________

---

### Task 3.3: Distributed Tracing
**New File:** `utils/tracing.py`  
**Action:**
1. Add OpenTelemetry dependencies
2. Initialize tracer in `main.py`
3. Add trace context propagation:
   - Twilio webhook → Pipecat → LLM → Tools
4. Instrument:
   - Database queries
   - External API calls
   - LLM invocations
5. Export to Google Cloud Trace

**Effort:** 5 days  
**Owner:** ___________

---

### Task 3.4: Durable State Management
**New Files:** `utils/state.py`, add Redis to docker-compose  
**Action:**
1. Add Redis container to docker-compose
2. Implement state persistence:
```python
class CallStateManager:
    def save_state(self, call_sid, state):
        redis.set(f"call:{call_sid}", json.dumps(state))
    
    def get_state(self, call_sid):
        return json.loads(redis.get(f"call:{call_sid}"))
```

3. Checkpoint state at each turn
4. Enable call recovery on process restart

**Effort:** 4 days  
**Owner:** ___________

---

## Phase 4: Testing & Quality (Weeks 9-11)

**Goal:** Establish quality gates and CI/CD

### Task 4.1: Unit Test Suite
**New Folder:** `tests/unit/`  
**Action:**
1. Test structure:
```
tests/
  unit/
    test_hedis_tools.py
    test_appointment_tools.py
    test_orchestrator.py
    test_pii_redaction.py
  integration/
    test_call_flow.py
    test_twilio_webhooks.py
  conftest.py  # Fixtures
```

2. Coverage targets:
   - Tools: 90%+
   - Orchestrator: 80%+
   - Utilities: 90%+

3. Mock external services (DB, Twilio, Google)

**Effort:** 10 days  
**Owner:** ___________

---

### Task 4.2: Integration Test Suite
**New Folder:** `tests/integration/`  
**Action:**
1. Test complete call flows:
   - Happy path HEDIS enrollment
   - Happy path appointment reschedule
   - Error recovery scenarios
   - Human handoff trigger

2. Use Docker Compose for test environment
3. Mock Twilio at webhook level

**Effort:** 5 days  
**Owner:** ___________

---

### Task 4.3: CI/CD Pipeline
**New File:** `.github/workflows/ci.yml`  
**Action:**
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt
      - name: Run tests
        run: pytest --cov=.
      - name: Run evals
        run: python eval/eval_runner.py --dry-run
```

**Effort:** 2 days  
**Owner:** ___________

---

### Task 4.4: Eval Regression Tracking
**Files:** `eval/eval_runner.py`, `routers/eval_api.py`  
**Action:**
1. Add eval baseline storage
2. Compare new runs against baseline
3. Alert on score regression > 10%
4. Add `/api/eval/baseline` endpoint

**Effort:** 3 days  
**Owner:** ___________

---

## Phase 5: Scalability (Weeks 12-14)

**Goal:** Enable horizontal scaling for production load

### Task 5.1: Distributed Call Queue
**File:** `routers/outbound_twillio.py`  
**Action:**
1. Change queue query to use row locking:
```sql
SELECT member_id, phone_number, campaign_name 
FROM campaign_target_member_call_list 
WHERE call_status = 'Not Called' 
FOR UPDATE SKIP LOCKED
LIMIT 1
```

2. Update status immediately after selection
3. Add worker ID tracking

**Effort:** 2 days  
**Owner:** ___________

---

### Task 5.2: Stateless Worker Design
**Documentation + Refactor**  
**Action:**
1. Audit all in-memory state
2. Move call state to Redis (Task 3.4)
3. Ensure workers can be horizontally scaled
4. Document deployment architecture

**Effort:** 3 days  
**Owner:** ___________

---

### Task 5.3: Package Structure
**Files:** `pyproject.toml`, refactor imports  
**Action:**
1. Create proper package structure:
```toml
[project]
name = "vaklab"
version = "0.1.0"
dependencies = [...]
```

2. Remove all `sys.path` manipulation
3. Use relative imports within package
4. Enable `pip install -e .` for development

**Effort:** 3 days  
**Owner:** ___________

---

## Success Criteria

### Phase 1 Complete When:
- [ ] No hardcoded credentials in codebase
- [ ] Twilio validation works in staging
- [ ] Connection pooling implemented
- [ ] Rate limiting active

### Phase 2 Complete When:
- [ ] All call events logged to database
- [ ] No PII in application logs
- [ ] Call recording works
- [ ] Consent tracked in database

### Phase 3 Complete When:
- [ ] Error recovery tested with chaos testing
- [ ] Human handoff demonstrated
- [ ] Traces visible in Cloud Trace
- [ ] Call state survives process restart

### Phase 4 Complete When:
- [ ] 80%+ code coverage
- [ ] All tests pass in CI
- [ ] Eval runs automatically on PR

### Phase 5 Complete When:
- [ ] Multiple workers can run without duplicate calls
- [ ] No sys.path manipulation
- [ ] Load test passes at 100 concurrent calls

---

## Resource Estimation

| Phase | Duration | Est. Engineering Days |
|-------|----------|----------------------|
| Phase 1 | 2 weeks | 10 days |
| Phase 2 | 3 weeks | 13 days |
| Phase 3 | 3 weeks | 19 days |
| Phase 4 | 3 weeks | 20 days |
| Phase 5 | 2 weeks | 8 days |
| **Total** | **14 weeks** | **70 engineer-days** |

**Assuming 1 engineer:** ~3.5 months  
**With 2 engineers:** ~2 months (phases can partially parallelize)
