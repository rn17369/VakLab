import json
from pathlib import Path

# Get latest HEDIS eval
eval_dir = Path('agents/outbound_agent/.adk/eval_history')
files = sorted([f for f in eval_dir.glob('outbound_agent_metna_eval_set_*.json')], 
               key=lambda x: x.stat().st_mtime, reverse=True)

latest = files[0]
print(f"📋 HEDIS Conversation Analysis - gemini-2.5-flash")
print(f"File: {latest.name}")
print("=" * 80)

with open(latest) as f:
    data = json.load(f)

case = data['eval_case_results'][0]
print(f"\nScenario: {case.get('eval_id', 'unknown')}")
print(f"Status: {case.get('final_eval_status')} (2=PASS)")

# Overall scores
print("\n📊 OVERALL SCORES:")
for metric in case.get('overall_eval_metric_results', []):
    name = metric.get('metric_name', '').replace('_v1', '').replace('rubric_based_', '')
    score = metric.get('score')
    if score is not None:
        print(f"  {name}: {score:.4f} ({score*100:.1f}%)")

# Parse conversation from events
session_details = case.get('session_details', {})
events = session_details.get('events', [])

# Extract user/agent turns
conversation = []
for event in events:
    content = event.get('content', {})
    role = content.get('role')
    parts = content.get('parts', [])
    
    if role and parts:
        text = None
        tools = []
        
        for part in parts:
            if part.get('text'):
                text = part['text']
            if part.get('function_call'):
                tools.append(part['function_call'].get('name'))
        
        if text or tools:
            conversation.append({'role': role, 'text': text, 'tools': tools})

print(f"\n💬 CONVERSATION ({len([c for c in conversation if c['role'] in ['user', 'model']])} turns):")
print("=" * 80)

for i, turn in enumerate(conversation):
    role = "USER" if turn['role'] == 'user' else "AGENT"
    text = turn['text'] or '[no text]'
    
    print(f"\n[Turn {i+1}] {role}:")
    print(f"  {text}")
    
    if turn['tools']:
        print(f"  🔧 TOOLS: {turn['tools']}")

# Analyze rubric failures
print(f"\n\n🔍 RUBRIC ANALYSIS:")
print("=" * 80)

# Get per-invocation results
per_inv = case.get('eval_metric_result_per_invocation', [])

for idx, inv_result in enumerate(per_inv):
    for metric_result in inv_result.get('eval_metric_results', []):
        if 'response_quality' in metric_result.get('metric_name', ''):
            rubric_results = metric_result.get('rubric_results', [])
            
            for rubric in rubric_results:
                rubric_id = rubric.get('rubric_id', '')
                score = rubric.get('score')
                reasoning = rubric.get('reasoning', '')
                
                if score is not None:
                    status = "✅ PASS" if score >= 0.8 else "❌ FAIL"
                    print(f"\n{status} Invocation {idx + 1} - {rubric_id}")
                    print(f"  Score: {score:.2f}")
                    if score < 0.8:
                        print(f"  Reasoning: {reasoning}")
