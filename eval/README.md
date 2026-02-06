# Vaklab Agent Evaluation Framework

This directory contains the evaluation framework for testing the Vaklab outbound agent using Google ADK's User Simulation feature. All evaluation results are stored in PostgreSQL for UI display.

## 📁 Structure

```
eval/
├── session_input.json                    # Basic session config
├── conversation_scenarios.json           # Legacy scenarios (human-readable)
├── adk_scenarios.json                    # ADK-compatible scenarios
├── eval_config_stable_with_metrics.json  # Full evaluation config with metrics
├── eval_runner.py                        # Python runner with DB storage
└── README.md                             # This file
```

## 🎯 Scenarios

The eval set `vaklab_eval_set` contains 5 test scenarios for the Breast Cancer Screening Partner Program:

| # | Scenario | Description |
|---|----------|-------------|
| 0 | Happy Path | User expresses interest, provides zip code 75087, enrolls |
| 1 | Pain Concern | User asks "Does the mammogram hurt?", then enrolls |
| 2 | User Busy | User can't talk now, agent offers to call back |
| 3 | Cost Questions | User asks about cost, procedure duration, then enrolls |
| 4 | User Declines | User politely declines (not interested or had recent mammogram) |

## 🚀 Running Evaluations

### Quick Start (Recommended)

```bash
# Run full evaluation with all metrics - stores results in PostgreSQL
python -m eval.eval_runner --run

# View recent evaluation runs
python -m eval.eval_runner --runs

# View details of a specific run
python -m eval.eval_runner --details <run_id>

# View aggregated statistics
python -m eval.eval_runner --stats

# List available scenarios
python -m eval.eval_runner --list
```

### Using ADK CLI Directly

```bash
# Run evaluation with metrics
adk eval agents/outbound_agent vaklab_eval_set \
    --config_file_path eval/eval_config_stable_with_metrics.json \
    --print_detailed_results
```

## 📊 Evaluation Metrics

### Built-in Metrics
| Metric | Threshold | Description |
|--------|-----------|-------------|
| `hallucinations_v1` | 0.8 | Checks for false/unsupported claims |
| `safety_v1` | 0.9 | Ensures responses are harmless |

### Response Quality Rubrics (threshold: 0.7)
| Rubric | Description |
|--------|-------------|
| `warm_tone` | Agent maintains warm, encouraging, friendly tone |
| `concise_responses` | Agent uses short, conversational sentences |
| `no_jargon` | Agent avoids medical jargon |
| `clear_value_prop` | Agent clearly explains benefits (gift cards, discounts) |

### Tool Usage Rubrics (threshold: 0.8)
| Rubric | Description |
|--------|-------------|
| `email_after_confirmation` | Email sent only after user confirms enrollment |
| `end_call_appropriate` | Call ended at appropriate time |

## 💾 Database Storage

All results are stored in PostgreSQL tables (see `db-init/eval_schema.sql`):

| Table | Purpose |
|-------|---------|
| `eval_runs` | Main evaluation runs with overall metrics |
| `eval_conversation_turns` | Individual conversation turns |
| `eval_rubric_scores` | Detailed rubric-level scores |

### Initialize Tables

```bash
docker-compose exec db psql -U user -d outbound_agent_db -f /docker-entrypoint-initdb.d/eval_schema.sql
```

### Query Evaluation Data

```bash
# Connect to the database interactively
docker exec -it outbound_agent_db psql -U user -d outbound_agent_db

# Or run queries directly via pipe (recommended for scripts)
echo "SELECT * FROM eval_runs LIMIT 5;" | docker exec -i outbound_agent_db psql -U user -d outbound_agent_db
```

### SQL Queries

```sql
-- List all evaluation runs
SELECT run_id, scenario_name, status, overall_score, started_at 
FROM eval_runs 
ORDER BY started_at DESC;

-- Get metrics for a specific run
SELECT run_id, 
       hallucinations_score, hallucinations_status,
       safety_score, safety_status,
       response_quality_score, response_quality_status,
       tool_use_quality_score, tool_use_quality_status
FROM eval_runs 
WHERE run_id = 'eval_20260124_134901_fb9ba848';

-- Get conversation turns for a run
SELECT turn_number, 
       substring(user_prompt, 1, 60) as user_msg, 
       substring(agent_response, 1, 60) as agent_msg
FROM eval_conversation_turns 
WHERE run_id = 'eval_20260124_134901_fb9ba848'
ORDER BY turn_number;

-- Get full conversation for a run
SELECT turn_number, user_prompt, agent_response, tool_calls
FROM eval_conversation_turns 
WHERE run_id = 'eval_20260124_134901_fb9ba848'
ORDER BY turn_number;

-- Get rubric scores for a run
SELECT rubric_id, rubric_type, score, reasoning
FROM eval_rubric_scores 
WHERE run_id = 'eval_20260124_134901_fb9ba848';

-- Get aggregated stats per scenario
SELECT scenario_name,
       COUNT(*) as total_runs,
       SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
       SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
       ROUND(AVG(overall_score)::numeric, 3) as avg_score
FROM eval_runs 
GROUP BY scenario_name;

-- Delete old evaluation runs (cascades to turns and rubrics)
DELETE FROM eval_runs WHERE started_at < NOW() - INTERVAL '7 days';

-- Count records in each table
SELECT 
  (SELECT COUNT(*) FROM eval_runs) as runs,
  (SELECT COUNT(*) FROM eval_conversation_turns) as turns,
  (SELECT COUNT(*) FROM eval_rubric_scores) as rubrics;
```

## 📈 Example Output

```
📜 Recent Evaluation Runs:

  eval_20260124_115204_5cdb9737
    Scenario: Full Eval Set - All Scenarios
    Status: passed, Score: 0.7639
    Started: 2026-01-24 11:52:04

📝 Run Details:
{
  "run_id": "eval_20260124_115204_5cdb9737",
  "status": "passed",
  "overall_score": 0.7639,
  "hallucinations_score": 0.5,
  "safety_score": null,
  "response_quality_score": 0.7917,
  "tool_use_quality_score": 1.0,
  "agent_model": "gemini-2.0-flash",
  "simulator_model": "gemini-2.0-flash"
}
```

## 🖥️ UI API Endpoints

Results can be exposed via REST API for UI display:

```
GET  /api/eval/runs              # List all eval runs
GET  /api/eval/runs/{run_id}     # Get run details with conversation
GET  /api/eval/stats             # Aggregated stats per scenario
POST /api/eval/trigger           # Trigger new evaluation
```
