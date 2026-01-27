"""
Evaluation Results API Router
Exposes evaluation results for UI display
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import json
from pathlib import Path

router = APIRouter(prefix="/api/eval", tags=["Evaluation"])

# --- Pydantic Models for API Response ---

class MetricScore(BaseModel):
    score: Optional[float]
    status: Optional[str]


class ConversationTurn(BaseModel):
    turn_number: int
    user_prompt: str
    agent_response: str
    tool_calls: List[dict]
    hallucinations_score: Optional[float]
    safety_score: Optional[float]
    response_quality_score: Optional[float]
    tool_use_quality_score: Optional[float]


class RubricScore(BaseModel):
    turn_number: int
    rubric_id: str
    rubric_type: str
    rubric_text: str
    score: float
    reasoning: Optional[str]


class EvalRunSummary(BaseModel):
    run_id: str
    scenario_id: str
    scenario_name: str
    status: str
    started_at: Optional[str]
    overall_score: Optional[float]


class EvalRunDetail(BaseModel):
    run_id: str
    scenario_id: str
    scenario_name: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    total_invocations: int
    overall_score: Optional[float]
    metrics: dict
    agent_model: str
    simulator_model: str
    conversation_turns: List[ConversationTurn]
    rubric_scores: List[RubricScore]


class ScenarioStats(BaseModel):
    scenario_id: str
    scenario_name: str
    total_runs: int
    passed_runs: int
    failed_runs: int
    avg_score: Optional[float]
    avg_hallucinations: Optional[float]
    avg_safety: Optional[float]
    avg_response_quality: Optional[float]
    avg_tool_use: Optional[float]


class ScenarioInfo(BaseModel):
    id: str
    name: str
    description: str
    starting_prompt: str
    conversation_plan: str


# --- File-based storage helper ---

def get_results_dir() -> Path:
    return Path(__file__).parent.parent / "eval" / "results"


def get_scenarios_file() -> Path:
    return Path(__file__).parent.parent / "eval" / "conversation_scenarios.json"


# --- API Endpoints ---

@router.get("/scenarios", response_model=List[ScenarioInfo])
async def list_scenarios():
    """Get all available evaluation scenarios"""
    scenarios_file = get_scenarios_file()
    if not scenarios_file.exists():
        raise HTTPException(status_code=404, detail="Scenarios file not found")
    
    with open(scenarios_file) as f:
        data = json.load(f)
    
    return data["scenarios"]


@router.get("/runs", response_model=List[EvalRunSummary])
async def list_eval_runs(
    limit: int = Query(50, ge=1, le=200),
    scenario_id: Optional[str] = None,
    status: Optional[str] = None
):
    """Get all evaluation runs with optional filtering"""
    results_dir = get_results_dir()
    index_file = results_dir / "index.json"
    
    if not index_file.exists():
        return []
    
    with open(index_file) as f:
        runs = json.load(f)
    
    # Filter by scenario
    if scenario_id:
        runs = [r for r in runs if r.get("scenario_id") == scenario_id]
    
    # Filter by status
    if status:
        runs = [r for r in runs if r.get("status") == status]
    
    return runs[:limit]


@router.get("/runs/{run_id}", response_model=EvalRunDetail)
async def get_eval_run_detail(run_id: str):
    """Get detailed results for a specific evaluation run"""
    results_dir = get_results_dir()
    result_file = results_dir / f"{run_id}.json"
    
    if not result_file.exists():
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    with open(result_file) as f:
        return json.load(f)


@router.get("/stats", response_model=List[ScenarioStats])
async def get_scenario_stats():
    """Get aggregated statistics per scenario"""
    results_dir = get_results_dir()
    index_file = results_dir / "index.json"
    
    if not index_file.exists():
        return []
    
    with open(index_file) as f:
        runs = json.load(f)
    
    # Aggregate by scenario
    stats_map = {}
    for run in runs:
        scenario_id = run.get("scenario_id")
        if scenario_id not in stats_map:
            stats_map[scenario_id] = {
                "scenario_id": scenario_id,
                "scenario_name": run.get("scenario_name", ""),
                "total_runs": 0,
                "passed_runs": 0,
                "failed_runs": 0,
                "scores": []
            }
        
        stats_map[scenario_id]["total_runs"] += 1
        if run.get("status") == "passed":
            stats_map[scenario_id]["passed_runs"] += 1
        elif run.get("status") == "failed":
            stats_map[scenario_id]["failed_runs"] += 1
        
        if run.get("overall_score") is not None:
            stats_map[scenario_id]["scores"].append(run["overall_score"])
    
    # Calculate averages
    results = []
    for scenario_id, data in stats_map.items():
        scores = data.pop("scores")
        data["avg_score"] = sum(scores) / len(scores) if scores else None
        # Other averages would need full run data
        data["avg_hallucinations"] = None
        data["avg_safety"] = None
        data["avg_response_quality"] = None
        data["avg_tool_use"] = None
        results.append(ScenarioStats(**data))
    
    return results


@router.get("/runs/{run_id}/conversation")
async def get_conversation(run_id: str):
    """Get just the conversation for a run (for chat-style display)"""
    results_dir = get_results_dir()
    result_file = results_dir / f"{run_id}.json"
    
    if not result_file.exists():
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    with open(result_file) as f:
        data = json.load(f)
    
    # Format as chat messages
    messages = []
    for turn in data.get("conversation_turns", []):
        messages.append({
            "role": "user",
            "content": turn["user_prompt"],
            "turn": turn["turn_number"]
        })
        messages.append({
            "role": "agent",
            "content": turn["agent_response"],
            "turn": turn["turn_number"],
            "tool_calls": turn.get("tool_calls", []),
            "metrics": {
                "hallucinations": turn.get("hallucinations_score"),
                "safety": turn.get("safety_score"),
                "response_quality": turn.get("response_quality_score"),
                "tool_use": turn.get("tool_use_quality_score")
            }
        })
    
    return {
        "run_id": run_id,
        "scenario_name": data.get("scenario_name"),
        "status": data.get("status"),
        "messages": messages
    }


@router.get("/runs/{run_id}/metrics")
async def get_run_metrics(run_id: str):
    """Get just the metrics for a run (for dashboard display)"""
    results_dir = get_results_dir()
    result_file = results_dir / f"{run_id}.json"
    
    if not result_file.exists():
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    with open(result_file) as f:
        data = json.load(f)
    
    return {
        "run_id": run_id,
        "scenario_name": data.get("scenario_name"),
        "status": data.get("status"),
        "overall_score": data.get("overall_score"),
        "metrics": data.get("metrics", {}),
        "rubric_scores": data.get("rubric_scores", [])
    }


@router.post("/trigger/{scenario_id}")
async def trigger_evaluation(
    scenario_id: str,
    dry_run: bool = Query(False, description="Run without metrics")
):
    """Trigger a new evaluation run for a scenario"""
    from eval.eval_runner import MetnaEvalRunner
    
    try:
        runner = MetnaEvalRunner(use_database=False)
        result = runner.run_scenario(scenario_id, with_metrics=not dry_run, dry_run=dry_run)
        return {
            "run_id": result.run_id,
            "status": "started",
            "message": f"Evaluation started for scenario: {scenario_id}"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
