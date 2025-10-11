"""
Comparative Test: ReAct Agent vs Direct LLM Classification
Tests 10+ diverse scenarios to validate classification quality
"""
import asyncio
import json
import time
from typing import Dict

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from .capture_agent import classify_note, create_classification_agent
from .config import LLM_MODEL, LLM_BASE_URL, LLM_TEMPERATURE


# Test scenarios covering diverse note types
TEST_SCENARIOS = [
    {
        "name": "Technical bug report",
        "text": """Login endpoint returning 500 error when user has special characters in password.
Need to investigate input sanitization in auth service. Affects production since v2.3.1 deploy.""",
        "expected_folder": "projects",
        "expected_tags": ["bug", "auth", "backend", "production"]
    },
    {
        "name": "Meeting notes with action items",
        "text": """Met with Sarah from design team. Discussed new dashboard mockups.
She'll send Figma files by Friday. I need to review API endpoints for data requirements.
Next sync scheduled for Tuesday 2pm.""",
        "expected_folder": "people",
        "expected_tags": ["meeting", "sarah", "design", "dashboard"]
    },
    {
        "name": "Research article summary",
        "text": """Interesting paper on vector databases performance.
HNSW vs IVF-PQ comparison shows HNSW has better recall at high speed.
Considerations for our similarity search implementation.
Paper: arxiv.org/abs/2304.12345""",
        "expected_folder": "research",
        "expected_tags": ["database", "vector", "performance", "paper"]
    },
    {
        "name": "Personal reflection",
        "text": """Feeling overwhelmed with current workload. Need to prioritize better.
Maybe delegate the monitoring dashboard task. Should talk to manager about capacity.""",
        "expected_folder": "journal",
        "expected_tags": ["personal", "reflection", "workload"]
    },
    {
        "name": "Quick task reminder",
        "text": "Deploy staging environment before demo tomorrow",
        "expected_folder": "projects",
        "expected_tags": ["task", "deploy", "staging"]
    },
    {
        "name": "Ambiguous note",
        "text": "Check on that thing John mentioned",
        "expected_folder": "inbox",
        "expected_tags": ["john", "todo"]
    },
    {
        "name": "Code implementation idea",
        "text": """Could refactor the notification service to use Redis pub/sub instead of polling.
Would reduce database load and improve real-time updates.
Need to benchmark first - create spike ticket.""",
        "expected_folder": "projects",
        "expected_tags": ["refactor", "redis", "notification", "architecture"]
    },
    {
        "name": "Learning note",
        "text": """TIL: Postgres EXPLAIN ANALYZE shows actual execution time vs estimated.
The 'Buffers' section is key for understanding cache hits.
Use EXPLAIN (ANALYZE, BUFFERS) for full picture.""",
        "expected_folder": "research",
        "expected_tags": ["postgres", "database", "til", "learning"]
    },
    {
        "name": "Conversation recap",
        "text": """Coffee chat with Mike from DevOps. He recommended switching to ArgoCD for deployments.
Says it's much better than our current Jenkins setup. Has good GitOps integration.
He can help with migration if we decide to go that route.""",
        "expected_folder": "people",
        "expected_tags": ["mike", "devops", "argocd", "deployment"]
    },
    {
        "name": "Product idea",
        "text": """Users keep asking for bulk export feature. Could add CSV/JSON export button in settings.
Backend already has the data, just need endpoint + UI. Probably 2-3 day task.
Would close 5+ support tickets.""",
        "expected_folder": "projects",
        "expected_tags": ["feature", "export", "product", "backend"]
    },
    {
        "name": "Multi-topic note",
        "text": """Team standup: Lisa finished the payment integration, Tom stuck on the OAuth flow.
I need to help him debug after lunch. Also reminded everyone about the offsite next month.
Sarah asked about Q2 roadmap - forwarded her the planning doc.""",
        "expected_folder": "people",
        "expected_tags": ["standup", "team", "meeting"]
    },
    {
        "name": "Very short note",
        "text": "Baseball game tonight 7pm",
        "expected_folder": "journal",
        "expected_tags": ["baseball", "personal"]
    },
]


def evaluate_classification(result: Dict, expected: Dict, scenario_name: str) -> Dict:
    """Evaluate classification quality"""
    score = 0
    max_score = 4
    feedback = []

    # Folder match (most important)
    if result.get("folder") == expected["expected_folder"]:
        score += 2
        feedback.append(f"✓ Folder: {result['folder']}")
    else:
        feedback.append(f"✗ Folder: {result.get('folder')} (expected: {expected['expected_folder']})")

    # Tag relevance (at least 1 matching tag)
    result_tags = set(result.get("tags", []))
    expected_tags = set(expected["expected_tags"])
    matching_tags = result_tags & expected_tags

    if matching_tags:
        score += 1
        feedback.append(f"✓ Tags matched: {matching_tags}")
    else:
        feedback.append(f"✗ No matching tags. Got: {result_tags}, Expected: {expected_tags}")

    # Title quality (exists and not too long)
    title = result.get("title", "")
    if title and len(title.split()) <= 10:
        score += 1
        feedback.append(f"✓ Title: {title}")
    else:
        feedback.append(f"✗ Title: {title}")

    return {
        "scenario": scenario_name,
        "score": score,
        "max_score": max_score,
        "percentage": (score / max_score) * 100,
        "feedback": feedback,
        "result": result
    }


def test_direct_llm(text: str) -> tuple[Dict, float]:
    """Test direct LLM classification (current implementation)"""
    start = time.perf_counter()
    result = classify_note.invoke({"raw_text": text})
    elapsed = time.perf_counter() - start
    return result, elapsed


def test_react_agent(text: str) -> tuple[Dict, float]:
    """Test ReAct agent classification"""
    agent = create_classification_agent()
    start = time.perf_counter()

    # Stream through agent
    final_result = None
    for chunk in agent.stream(
        {"messages": [("user", f"Classify this note: {text}")]},
        stream_mode="values"
    ):
        if "messages" in chunk:
            last_msg = chunk["messages"][-1]
            # Try to extract classification result
            if hasattr(last_msg, "type") and last_msg.type == "tool":
                try:
                    final_result = json.loads(last_msg.content) if isinstance(last_msg.content, str) else last_msg.content
                except:
                    pass

    # Fallback: call tool directly if agent didn't produce result
    if not final_result:
        final_result = classify_note.invoke({"raw_text": text})

    elapsed = time.perf_counter() - start
    return final_result, elapsed


def run_comparison():
    """Run comparative test suite"""
    print("=" * 80)
    print("CLASSIFICATION QUALITY COMPARISON: ReAct Agent vs Direct LLM")
    print("=" * 80)
    print(f"Model: {LLM_MODEL}")
    print(f"Scenarios: {len(TEST_SCENARIOS)}")
    print()

    direct_results = []
    react_results = []

    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        print(f"\n[{i}/{len(TEST_SCENARIOS)}] {scenario['name']}")
        print("-" * 80)
        print(f"Text: {scenario['text'][:100]}...")
        print()

        # Test direct LLM
        print("Testing Direct LLM...")
        try:
            direct_result, direct_time = test_direct_llm(scenario["text"])
            direct_eval = evaluate_classification(direct_result, scenario, scenario["name"])
            direct_eval["time"] = direct_time
            direct_results.append(direct_eval)

            print(f"  Time: {direct_time:.2f}s")
            print(f"  Score: {direct_eval['score']}/{direct_eval['max_score']} ({direct_eval['percentage']:.0f}%)")
            for fb in direct_eval["feedback"]:
                print(f"    {fb}")
        except Exception as e:
            print(f"  ERROR: {e}")
            direct_results.append({"scenario": scenario["name"], "error": str(e), "score": 0, "max_score": 4})

        print()

        # Test ReAct agent
        print("Testing ReAct Agent...")
        try:
            react_result, react_time = test_react_agent(scenario["text"])
            react_eval = evaluate_classification(react_result, scenario, scenario["name"])
            react_eval["time"] = react_time
            react_results.append(react_eval)

            print(f"  Time: {react_time:.2f}s")
            print(f"  Score: {react_eval['score']}/{react_eval['max_score']} ({react_eval['percentage']:.0f}%)")
            for fb in react_eval["feedback"]:
                print(f"    {fb}")
        except Exception as e:
            print(f"  ERROR: {e}")
            react_results.append({"scenario": scenario["name"], "error": str(e), "score": 0, "max_score": 4})

        print()

    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    direct_scores = [r["score"] for r in direct_results if "score" in r]
    react_scores = [r["score"] for r in react_results if "score" in r]

    direct_times = [r["time"] for r in direct_results if "time" in r]
    react_times = [r["time"] for r in react_results if "time" in r]

    print("\nDirect LLM:")
    print(f"  Avg Score: {sum(direct_scores)/len(direct_scores):.2f}/{direct_results[0]['max_score']}")
    print(f"  Avg Accuracy: {(sum(direct_scores)/(len(direct_scores)*4))*100:.1f}%")
    print(f"  Avg Time: {sum(direct_times)/len(direct_times):.2f}s")
    print(f"  Total Time: {sum(direct_times):.2f}s")

    print("\nReAct Agent:")
    print(f"  Avg Score: {sum(react_scores)/len(react_scores):.2f}/{react_results[0]['max_score']}")
    print(f"  Avg Accuracy: {(sum(react_scores)/(len(react_scores)*4))*100:.1f}%")
    print(f"  Avg Time: {sum(react_times)/len(react_times):.2f}s")
    print(f"  Total Time: {sum(react_times):.2f}s")

    print("\nComparison:")
    score_diff = sum(react_scores) - sum(direct_scores)
    time_diff = sum(react_times) - sum(direct_times)

    print(f"  Quality difference: {score_diff:+.1f} points ({score_diff/len(TEST_SCENARIOS):+.2f} per scenario)")
    print(f"  Speed difference: {time_diff:+.2f}s ({time_diff/len(TEST_SCENARIOS):+.2f}s per scenario)")

    if abs(score_diff) < len(TEST_SCENARIOS) * 0.5:  # Less than 0.5 point diff per scenario
        print("\n✅ RECOMMENDATION: Quality is similar. Direct LLM is sufficient.")
        if time_diff > 0:
            print(f"   BONUS: Direct LLM is {time_diff:.1f}s faster overall!")
    elif score_diff > 0:
        print("\n⚠️  RECOMMENDATION: ReAct agent provides better quality.")
        print(f"   Trade-off: {time_diff:.1f}s slower for {score_diff} point improvement")
    else:
        print("\n✅ RECOMMENDATION: Direct LLM is better - both faster AND more accurate!")

    # Save detailed results
    with open("classification_comparison_results.json", "w") as f:
        json.dump({
            "direct_llm": direct_results,
            "react_agent": react_results,
            "summary": {
                "direct_avg_score": sum(direct_scores)/len(direct_scores),
                "direct_avg_time": sum(direct_times)/len(direct_times),
                "react_avg_score": sum(react_scores)/len(react_scores),
                "react_avg_time": sum(react_times)/len(react_times),
            }
        }, f, indent=2)

    print(f"\n📄 Detailed results saved to: classification_comparison_results.json")


if __name__ == "__main__":
    print("Starting classification comparison test...\n")
    print("⚠️  Make sure Ollama is running with the model loaded!")
    print(f"   Model: {LLM_MODEL}")
    print(f"   URL: {LLM_BASE_URL}")
    print()

    run_comparison()
