"""
Metna Agent Evaluation Framework
Runs user simulation evaluations with metrics using ADK CLI and stores results in PostgreSQL
"""

import os
import json
import uuid
import asyncio
import subprocess
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv
from loguru import logger

load_dotenv(override=True)


# --- Data Classes ---

@dataclass
class ConversationTurn:
    turn_number: int
    user_prompt: str
    agent_response: str
    tool_calls: List[Dict]
    hallucinations_score: Optional[float] = None
    hallucinations_status: Optional[str] = None
    safety_score: Optional[float] = None
    safety_status: Optional[str] = None
    response_quality_score: Optional[float] = None
    tool_use_quality_score: Optional[float] = None
    response_latency_ms: Optional[int] = None


@dataclass
class RubricScore:
    turn_number: int
    rubric_id: str
    rubric_type: str
    rubric_text: str
    score: float
    reasoning: str


@dataclass
class EvalRunResult:
    run_id: str
    scenario_id: str
    scenario_name: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_invocations: int
    campaign_type: str = "hedis"  # Track which campaign was evaluated
    overall_score: Optional[float] = None
    hallucinations_score: Optional[float] = None
    hallucinations_status: Optional[str] = None
    safety_score: Optional[float] = None
    safety_status: Optional[str] = None
    response_quality_score: Optional[float] = None
    response_quality_status: Optional[str] = None
    tool_use_quality_score: Optional[float] = None
    tool_use_quality_status: Optional[str] = None
    agent_model: str = "gemini-2.5-flash"
    simulator_model: str = "gemini-2.5-flash"
    config_used: Dict = None
    conversation_turns: List[ConversationTurn] = None
    rubric_scores: List[RubricScore] = None
    
    def __post_init__(self):
        if self.config_used is None:
            self.config_used = {}
        if self.conversation_turns is None:
            self.conversation_turns = []
        if self.rubric_scores is None:
            self.rubric_scores = []


# --- Database Storage ---

class EvalResultsStorage:
    """Stores evaluation results in PostgreSQL for UI display"""
    
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "outbound_agent_db"),
            user=os.getenv("DB_USER", "user"),
            password=os.getenv("DB_PASSWORD", "password")
        )
        self.conn.autocommit = True
    
    def save_eval_run(self, result: EvalRunResult) -> str:
        """Save a complete evaluation run with all turns and rubrics"""
        cursor = self.conn.cursor()
        
        try:
            # Insert main run record
            campaign_type = getattr(result, 'campaign_type', 'hedis')
            cursor.execute("""
                INSERT INTO eval_runs (
                    run_id, scenario_id, scenario_name, campaign_type, status,
                    started_at, completed_at, total_invocations,
                    overall_score, hallucinations_score, hallucinations_status,
                    safety_score, safety_status,
                    response_quality_score, response_quality_status,
                    tool_use_quality_score, tool_use_quality_status,
                    agent_model, simulator_model, config_used
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (run_id) DO UPDATE SET
                    campaign_type = EXCLUDED.campaign_type,
                    status = EXCLUDED.status,
                    completed_at = EXCLUDED.completed_at,
                    total_invocations = EXCLUDED.total_invocations,
                    overall_score = EXCLUDED.overall_score,
                    hallucinations_score = EXCLUDED.hallucinations_score,
                    hallucinations_status = EXCLUDED.hallucinations_status,
                    safety_score = EXCLUDED.safety_score,
                    safety_status = EXCLUDED.safety_status,
                    response_quality_score = EXCLUDED.response_quality_score,
                    response_quality_status = EXCLUDED.response_quality_status,
                    tool_use_quality_score = EXCLUDED.tool_use_quality_score,
                    tool_use_quality_status = EXCLUDED.tool_use_quality_status
            """, (
                result.run_id, result.scenario_id, result.scenario_name, campaign_type,
                result.status, result.started_at, result.completed_at,
                result.total_invocations, result.overall_score,
                result.hallucinations_score, result.hallucinations_status,
                result.safety_score, result.safety_status,
                result.response_quality_score, result.response_quality_status,
                result.tool_use_quality_score, result.tool_use_quality_status,
                result.agent_model, result.simulator_model, Json(result.config_used)
            ))
            
            # Delete old turns/rubrics if updating
            cursor.execute("DELETE FROM eval_conversation_turns WHERE run_id = %s", (result.run_id,))
            cursor.execute("DELETE FROM eval_rubric_scores WHERE run_id = %s", (result.run_id,))
            
            # Insert conversation turns
            for turn in result.conversation_turns:
                cursor.execute("""
                    INSERT INTO eval_conversation_turns (
                        run_id, turn_number, user_prompt, agent_response,
                        tool_calls, hallucinations_score, hallucinations_status,
                        safety_score, safety_status, response_quality_score,
                        tool_use_quality_score, response_latency_ms
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    result.run_id, turn.turn_number, turn.user_prompt,
                    turn.agent_response, Json(turn.tool_calls),
                    turn.hallucinations_score, turn.hallucinations_status,
                    turn.safety_score, turn.safety_status,
                    turn.response_quality_score, turn.tool_use_quality_score,
                    turn.response_latency_ms
                ))
            
            # Insert rubric scores
            campaign_type = getattr(result, 'campaign_type', 'hedis')
            for rubric in result.rubric_scores:
                cursor.execute("""
                    INSERT INTO eval_rubric_scores (
                        run_id, turn_number, rubric_id, rubric_type,
                        campaign_type, rubric_text, score, reasoning
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    result.run_id, rubric.turn_number, rubric.rubric_id,
                    rubric.rubric_type, campaign_type, rubric.rubric_text,
                    rubric.score, rubric.reasoning
                ))
            
            logger.info(f"✅ Saved eval run {result.run_id} to database")
            return result.run_id
            
        except Exception as e:
            logger.error(f"Failed to save eval run: {e}")
            raise
        finally:
            cursor.close()
    
    def get_all_runs(self, limit: int = 50) -> List[Dict]:
        """Get all evaluation runs for UI display"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT run_id, scenario_id, scenario_name, status,
                   started_at, completed_at, total_invocations,
                   overall_score, hallucinations_score, safety_score,
                   response_quality_score, tool_use_quality_score
            FROM eval_runs
            ORDER BY started_at DESC
            LIMIT %s
        """, (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()
        return results
    
    def get_run_details(self, run_id: str) -> Dict:
        """Get detailed results for a specific run including conversation"""
        cursor = self.conn.cursor()
        
        # Get run info
        cursor.execute("SELECT * FROM eval_runs WHERE run_id = %s", (run_id,))
        columns = [desc[0] for desc in cursor.description]
        run_row = cursor.fetchone()
        if not run_row:
            return None
        run = dict(zip(columns, run_row))
        
        # Get conversation turns
        cursor.execute("""
            SELECT * FROM eval_conversation_turns 
            WHERE run_id = %s ORDER BY turn_number
        """, (run_id,))
        columns = [desc[0] for desc in cursor.description]
        run["conversation_turns"] = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # Get rubric scores
        cursor.execute("""
            SELECT * FROM eval_rubric_scores
            WHERE run_id = %s ORDER BY turn_number, rubric_id
        """, (run_id,))
        columns = [desc[0] for desc in cursor.description]
        run["rubric_scores"] = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        return run
    
    def get_scenario_stats(self) -> List[Dict]:
        """Get aggregated stats per scenario for dashboard"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                scenario_id,
                scenario_name,
                COUNT(*) as total_runs,
                SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed_runs,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_runs,
                AVG(overall_score) as avg_score,
                AVG(hallucinations_score) as avg_hallucinations,
                AVG(safety_score) as avg_safety,
                AVG(response_quality_score) as avg_response_quality,
                AVG(tool_use_quality_score) as avg_tool_use
            FROM eval_runs
            GROUP BY scenario_id, scenario_name
            ORDER BY scenario_name
        """)
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()
        return results
    
    def close(self):
        self.conn.close()


# --- Evaluation Runner ---

class MetnaEvalRunner:
    """Runs evaluations against Metna agent using ADK CLI and stores results in DB"""
    
    def __init__(self, campaign: str = "hedis"):
        self.eval_dir = Path(__file__).parent
        self.project_root = self.eval_dir.parent
        self.agent_module = "agents/outbound_agent"
        self.campaign = campaign
        self.storage = EvalResultsStorage()
        
        # Select eval set and config based on campaign
        if campaign == "appointment":
            self.eval_set_name = "appointment_eval_set"
            config_file = self.eval_dir / "eval_config_appointment.json"
        else:  # Default to HEDIS
            self.eval_set_name = "metna_eval_set"
            config_file = self.eval_dir / "eval_config_stable_with_metrics.json"
        
        # Load scenarios from adk_scenarios.json (legacy, can be removed later)
        scenarios_file = self.eval_dir / "adk_scenarios.json"
        if scenarios_file.exists():
            with open(scenarios_file) as f:
                data = json.load(f)
                self.scenarios = data.get("scenarios", [])
        else:
            self.scenarios = []
        
        # Load config with metrics
        with open(config_file) as f:
            self.config_data = json.load(f)
    
    def _parse_adk_output(self, output: str) -> Dict:
        """Parse ADK CLI output to extract metrics, conversation turns, and rubric scores"""
        result = {
            "status": "unknown",
            "metrics": {},
            "conversation_turns": [],
            "rubric_scores": []
        }
        
        # Parse overall status from "Overall Eval Status: PASSED"
        overall_match = re.search(r'Overall Eval Status:\s*(\w+)', output, re.IGNORECASE)
        if overall_match:
            status = overall_match.group(1).upper()
            result["status"] = "passed" if status == "PASSED" else "failed"
        elif "All tests passed" in output:
            result["status"] = "passed"
        
        # Parse metric scores
        # Format: "Metric: hallucinations_v1, Status: PASSED, Score: 0.8, Threshold: 0.8"
        metric_pattern = r'Metric:\s*(\w+),\s*Status:\s*(\w+),\s*Score:\s*([\d.]+|None)'
        for match in re.finditer(metric_pattern, output, re.IGNORECASE):
            metric_name = match.group(1)
            status = match.group(2).upper()
            score_str = match.group(3)
            score = float(score_str) if score_str != "None" else None
            result["metrics"][metric_name] = {
                "score": score,
                "status": "passed" if status == "PASSED" else ("not_evaluated" if status == "NOT_EVALUATED" else "failed")
            }
        
        # Parse rubric scores
        # Format: "Rubric: The agent maintains..., Score: 1.0, Reasoning: ..."
        rubric_pattern = r'Rubric:\s*([^,]+),\s*Score:\s*([\d.]+)'
        for match in re.finditer(rubric_pattern, output):
            rubric_text = match.group(1).strip()
            score = float(match.group(2))
            # Generate a simple ID from the text
            rubric_id = rubric_text[:30].lower().replace(" ", "_").replace(",", "")
            result["rubric_scores"].append({
                "rubric_id": rubric_id,
                "rubric_text": rubric_text,
                "score": score
            })
        
        # Parse conversation turns from log output
        # Agent responses are logged like: "Response received from the model"
        # User prompts come from the simulator
        turn_number = 0
        
        # Look for user/agent message patterns in the logs
        # Pattern: lines containing text like "User:", "Agent:", or similar from eval output
        lines = output.split('\n')
        current_user = None
        current_agent = None
        
        for line in lines:
            # Check for user simulator messages
            if 'User:' in line or 'Simulated User:' in line or 'user_prompt' in line:
                user_match = re.search(r'(?:User:|Simulated User:|user_prompt["\']?:\s*["\'])(.+)', line)
                if user_match:
                    current_user = user_match.group(1).strip().strip('"\'')
            
            # Check for agent responses  
            elif 'Agent:' in line or 'agent_response' in line or 'Metna:' in line:
                agent_match = re.search(r'(?:Agent:|Metna:|agent_response["\']?:\s*["\'])(.+)', line)
                if agent_match:
                    current_agent = agent_match.group(1).strip().strip('"\'')
            
            # If we have both a user prompt and agent response, record the turn
            if current_user and current_agent:
                turn_number += 1
                result["conversation_turns"].append({
                    "turn_number": turn_number,
                    "user_prompt": current_user,
                    "agent_response": current_agent,
                    "tool_calls": []
                })
                current_user = None
                current_agent = None
        
        # If no turns were parsed from logs, try to extract from detailed results JSON
        if not result["conversation_turns"]:
            # Look for JSON-like conversation blocks in the output
            json_match = re.search(r'\{[^{}]*"conversation"[^{}]*\[.*?\][^{}]*\}', output, re.DOTALL)
            if json_match:
                try:
                    conv_data = json.loads(json_match.group(0))
                    for i, msg in enumerate(conv_data.get("conversation", [])):
                        if msg.get("role") == "user":
                            result["conversation_turns"].append({
                                "turn_number": i + 1,
                                "user_prompt": msg.get("content", ""),
                                "agent_response": "",
                                "tool_calls": []
                            })
                except json.JSONDecodeError:
                    pass
        
        return result
    
    def _parse_eval_history_files(self) -> List[ConversationTurn]:
        """Parse conversation turns from ADK eval history JSON files"""
        eval_history_dir = self.project_root / "agents/outbound_agent/.adk/eval_history"
        
        if not eval_history_dir.exists():
            logger.warning(f"Eval history directory not found: {eval_history_dir}")
            return []
        
        # Find the most recent eval result file
        result_files = sorted(
            eval_history_dir.glob("*.evalset_result.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        if not result_files:
            logger.warning("No eval result files found in history")
            return []
        
        # Parse the most recent file
        latest_file = result_files[0]
        logger.info(f"📂 Parsing conversation from: {latest_file.name}")
        
        turns = []
        try:
            with open(latest_file) as f:
                data = json.load(f)
            
            turn_number = 0
            for case_result in data.get("eval_case_results", []):
                invocations = case_result.get("eval_metric_result_per_invocation", [])
                if not invocations:
                    continue
                
                for inv in invocations:
                    if not inv:
                        continue
                    actual = inv.get("actual_invocation")
                    if not actual:
                        continue
                    
                    user_content = actual.get("user_content") or {}
                    final_response = actual.get("final_response") or {}
                    
                    # Extract user text
                    user_text = ""
                    for part in (user_content.get("parts") or []):
                        if part and part.get("text"):
                            user_text = part["text"]
                            break
                    
                    # Extract agent response text
                    agent_text = ""
                    for part in (final_response.get("parts") or []):
                        if part and part.get("text"):
                            agent_text = part["text"]
                            break
                    
                    if user_text or agent_text:
                        turn_number += 1
                        # Extract tool calls from intermediate_data
                        tool_calls = []
                        intermediate = actual.get("intermediate_data") or {}
                        for event in (intermediate.get("invocation_events") or []):
                            if event and event.get("function_call"):
                                tool_calls.append(event["function_call"])
                        
                        turns.append(ConversationTurn(
                            turn_number=turn_number,
                            user_prompt=user_text.strip(),
                            agent_response=agent_text.strip(),
                            tool_calls=tool_calls
                        ))
            
            logger.info(f"✅ Extracted {len(turns)} conversation turns from eval history")
            
        except Exception as e:
            logger.error(f"Failed to parse eval history file: {e}")
        
        return turns
    
    def run_evaluation(self) -> EvalRunResult:
        """Run evaluation using ADK CLI and store results in database"""
        
        run_id = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        scenario_name = "Full Eval Set - All Scenarios"
        
        logger.info(f"🚀 Starting evaluation: {scenario_name} (run_id: {run_id})")
        
        sim_model = self.config_data.get("user_simulator_config", {}).get("model", "gemini-2.5-flash")
        
        # Create initial result
        result = EvalRunResult(
            run_id=run_id,
            scenario_id="full_eval_set",
            scenario_name=scenario_name,
            campaign_type=self.campaign,
            status="running",
            started_at=datetime.now(),
            completed_at=None,
            total_invocations=0,
            agent_model="gemini-2.5-flash",
            simulator_model=sim_model,
            config_used=self.config_data
        )
        
        # Save initial state
        self.storage.save_eval_run(result)
        
        try:
            # Run ADK eval CLI with campaign-appropriate config
            if self.campaign == "appointment":
                config_path = self.eval_dir / "eval_config_appointment.json"
            else:
                config_path = self.eval_dir / "eval_config_stable_with_metrics.json"
            
            cmd = [
                "adk", "eval",
                self.agent_module,
                self.eval_set_name,
                "--config_file_path", str(config_path),
                "--print_detailed_results"
            ]
            
            logger.info(f"Running {self.campaign} evaluation: {' '.join(cmd)}")
            
            process = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            output = process.stdout + process.stderr
            logger.info(f"ADK CLI output length: {len(output)} chars")
            
            # Parse the output
            parsed = self._parse_adk_output(output)
            
            # Update result with parsed metrics
            if "hallucinations_v1" in parsed["metrics"]:
                m = parsed["metrics"]["hallucinations_v1"]
                result.hallucinations_score = m["score"]
                result.hallucinations_status = m["status"]
            
            if "safety_v1" in parsed["metrics"]:
                m = parsed["metrics"]["safety_v1"]
                result.safety_score = m["score"]
                result.safety_status = m["status"]
            
            if "rubric_based_final_response_quality_v1" in parsed["metrics"]:
                m = parsed["metrics"]["rubric_based_final_response_quality_v1"]
                result.response_quality_score = m["score"]
                result.response_quality_status = m["status"]
            
            if "rubric_based_tool_use_quality_v1" in parsed["metrics"]:
                m = parsed["metrics"]["rubric_based_tool_use_quality_v1"]
                result.tool_use_quality_score = m["score"]
                result.tool_use_quality_status = m["status"]
            
            # Add rubric scores
            for rs in parsed["rubric_scores"]:
                rubric = RubricScore(
                    turn_number=0,
                    rubric_id=rs["rubric_id"],
                    rubric_type="response_quality",
                    rubric_text=rs.get("rubric_text", ""),
                    score=rs["score"],
                    reasoning=""
                )
                result.rubric_scores.append(rubric)
            
            # Add conversation turns from parsed output
            for turn_data in parsed["conversation_turns"]:
                turn = ConversationTurn(
                    turn_number=turn_data["turn_number"],
                    user_prompt=turn_data["user_prompt"],
                    agent_response=turn_data["agent_response"],
                    tool_calls=turn_data.get("tool_calls", [])
                )
                result.conversation_turns.append(turn)
            
            # If no turns from CLI output, try to parse from ADK eval history files
            if not result.conversation_turns:
                result.conversation_turns = self._parse_eval_history_files()
            
            logger.info(f"📝 Parsed {len(result.conversation_turns)} conversation turns")
            
            # Calculate overall score
            scores = [s for s in [
                result.hallucinations_score,
                result.safety_score,
                result.response_quality_score,
                result.tool_use_quality_score
            ] if s is not None]
            
            if scores:
                result.overall_score = sum(scores) / len(scores)
            
            # Set status based on exit code and parsed result
            if process.returncode == 0:
                result.status = parsed["status"] if parsed["status"] != "unknown" else "passed"
            else:
                result.status = "failed"
            
            result.completed_at = datetime.now()
            
            # Log the full output for debugging
            if process.returncode != 0:
                logger.warning(f"ADK CLI returned non-zero exit code: {process.returncode}")
                logger.debug(f"Output: {output[:2000]}")
            
        except subprocess.TimeoutExpired:
            logger.error("Evaluation timed out after 5 minutes")
            result.status = "failed"
            result.completed_at = datetime.now()
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            import traceback
            traceback.print_exc()
            result.status = "failed"
            result.completed_at = datetime.now()
        
        # Save final result
        self.storage.save_eval_run(result)
        
        logger.info(f"✅ Evaluation complete: {result.status} (score: {result.overall_score})")
        return result
    
    def get_all_runs(self, limit: int = 50) -> List[Dict]:
        """Get all evaluation runs from database"""
        return self.storage.get_all_runs(limit)
    
    def get_run_details(self, run_id: str) -> Dict:
        """Get detailed results for a specific run"""
        return self.storage.get_run_details(run_id)
    
    def get_scenario_stats(self) -> List[Dict]:
        """Get aggregated stats per scenario"""
        return self.storage.get_scenario_stats()


def main():
    """CLI entry point for running evaluations"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Metna Agent Evaluation Runner")
    parser.add_argument("--run", action="store_true", help="Run evaluation with metrics")
    parser.add_argument("--campaign", type=str, default="hedis", choices=["hedis", "appointment"], 
                        help="Campaign type to evaluate (default: hedis)")
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    parser.add_argument("--stats", action="store_true", help="Show evaluation statistics")
    parser.add_argument("--runs", action="store_true", help="List recent evaluation runs")
    parser.add_argument("--details", type=str, help="Show details for a specific run ID")
    
    args = parser.parse_args()
    
    runner = MetnaEvalRunner(campaign=args.campaign)
    
    if args.list:
        print("\n📋 Available Scenarios:\n")
        for i, s in enumerate(runner.scenarios):
            print(f"  [{i}] {s['starting_prompt']}")
            print(f"      Plan: {s['conversation_plan'][:80]}...\n")
        return
    
    if args.stats:
        stats = runner.get_scenario_stats()
        print("\n📊 Scenario Statistics:\n")
        if not stats:
            print("  No evaluation runs yet.")
        for stat in stats:
            print(f"  {stat['scenario_name']}")
            print(f"    Total runs: {stat['total_runs']}, Passed: {stat['passed_runs']}, Failed: {stat['failed_runs']}")
            if stat['avg_score']:
                print(f"    Avg score: {float(stat['avg_score']):.2f}")
            else:
                print("    Avg score: N/A")
            print()
        return
    
    if args.runs:
        runs = runner.get_all_runs()
        print("\n📜 Recent Evaluation Runs:\n")
        if not runs:
            print("  No evaluation runs yet.")
        for run in runs:
            print(f"  {run['run_id']}")
            print(f"    Scenario: {run['scenario_name']}")
            print(f"    Status: {run['status']}, Score: {run['overall_score']}")
            print(f"    Started: {run['started_at']}\n")
        return
    
    if args.details:
        details = runner.get_run_details(args.details)
        if not details:
            print(f"Run {args.details} not found.")
            return
        print(f"\n📝 Run Details: {args.details}\n")
        print(json.dumps(details, indent=2, default=str))
        return
    
    if args.run:
        runner.run_evaluation()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
