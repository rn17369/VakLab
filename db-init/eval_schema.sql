-- Evaluation Results Tables for Agent Testing Framework
-- These tables store simulated conversations and metrics for UI display

-- Evaluation Runs - Each time you run an evaluation
CREATE TABLE IF NOT EXISTS eval_runs (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(100) UNIQUE NOT NULL,
    scenario_id VARCHAR(100) NOT NULL,
    scenario_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'running', -- running, passed, failed, not_evaluated
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    total_invocations INTEGER DEFAULT 0,
    
    -- Overall Metrics
    overall_score DECIMAL(5,4),
    hallucinations_score DECIMAL(5,4),
    hallucinations_status VARCHAR(50),
    safety_score DECIMAL(5,4),
    safety_status VARCHAR(50),
    response_quality_score DECIMAL(5,4),
    response_quality_status VARCHAR(50),
    tool_use_quality_score DECIMAL(5,4),
    tool_use_quality_status VARCHAR(50),
    
    -- Metadata
    agent_model VARCHAR(100),
    simulator_model VARCHAR(100),
    config_used JSONB
);

-- Conversation Turns - Each message in a simulated conversation
CREATE TABLE IF NOT EXISTS eval_conversation_turns (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(100) REFERENCES eval_runs(run_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    
    -- Messages
    user_prompt TEXT,
    agent_response TEXT,
    
    -- Tool Calls (JSON array of tool calls)
    tool_calls JSONB,
    
    -- Per-turn Metrics
    hallucinations_score DECIMAL(5,4),
    hallucinations_status VARCHAR(50),
    safety_score DECIMAL(5,4),
    safety_status VARCHAR(50),
    response_quality_score DECIMAL(5,4),
    tool_use_quality_score DECIMAL(5,4),
    
    -- Timing
    response_latency_ms INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rubric Scores - Detailed rubric-level scoring
CREATE TABLE IF NOT EXISTS eval_rubric_scores (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(100) REFERENCES eval_runs(run_id) ON DELETE CASCADE,
    turn_number INTEGER,
    rubric_id VARCHAR(100) NOT NULL,
    rubric_type VARCHAR(50), -- 'response_quality' or 'tool_use'
    rubric_text TEXT,
    score DECIMAL(5,4),
    reasoning TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast querying
CREATE INDEX IF NOT EXISTS idx_eval_runs_scenario ON eval_runs(scenario_id);
CREATE INDEX IF NOT EXISTS idx_eval_runs_status ON eval_runs(status);
CREATE INDEX IF NOT EXISTS idx_eval_turns_run ON eval_conversation_turns(run_id);
CREATE INDEX IF NOT EXISTS idx_eval_rubrics_run ON eval_rubric_scores(run_id);
