#!/usr/bin/env python3
"""
Comparison: Custom Agentic Loop vs LangGraph with SLMs
Tests both approaches with Qwen3 and Gemma3 via Ollama
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Annotated
from dataclasses import dataclass

# LangGraph imports
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

# LiteLLM for custom implementation
import litellm

# Configure LiteLLM
import os
os.environ['LITELLM_LOG'] = 'ERROR'  # Reduce noise

# ============================================================================
# SHARED TOOLS - LangChain format
# ============================================================================

@tool
def calculate(expression: str) -> Dict:
    """Calculate a mathematical expression.

    Args:
        expression: The mathematical expression to evaluate (e.g., "25 * 4 + 10")

    Returns:
        Dictionary with expression and result, or error
    """
    if not expression:
        return {"error": "No expression provided"}
    try:
        result = eval(expression, {"__builtins__": {}})
        return {"expression": expression, "result": result}
    except Exception as e:
        return {"error": str(e)}

@tool
def get_current_time(timezone: str = "UTC") -> Dict:
    """Get the current date and time.

    Args:
        timezone: Timezone name (e.g., UTC, Europe/London)

    Returns:
        Dictionary with time, date, and timezone
    """
    now = datetime.now()
    return {
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "timezone": timezone
    }

@tool
def get_weather(city: str) -> Dict:
    """Get weather information for a city.

    Args:
        city: The city name (e.g., London, Tokyo)

    Returns:
        Dictionary with temperature and weather condition
    """
    if not city:
        return {"error": "No city provided"}
    weather_data = {
        "London": {"temp": "15°C", "condition": "Cloudy"},
        "Tokyo": {"temp": "22°C", "condition": "Sunny"},
        "New York": {"temp": "18°C", "condition": "Partly cloudy"},
    }
    return weather_data.get(city, {"temp": "20°C", "condition": "Clear"})

# Tool list for LangGraph
TOOLS = [calculate, get_current_time, get_weather]

# ============================================================================
# LANGGRAPH IMPLEMENTATION
# ============================================================================

async def run_langgraph_agent(query: str, model_name: str) -> Dict:
    """Run query using LangGraph's create_react_agent"""
    start_time = time.time()

    # Create ChatOllama model
    llm = ChatOllama(
        model=model_name,
        temperature=0.1,
    )

    # Create ReAct agent
    agent = create_react_agent(llm, TOOLS)

    # Run agent
    try:
        result = await agent.ainvoke({
            "messages": [HumanMessage(content=query)]
        })

        # Extract final response
        messages = result.get("messages", [])
        final_message = messages[-1] if messages else None
        final_answer = final_message.content if final_message else None

        execution_time = time.time() - start_time

        return {
            "success": True,
            "answer": final_answer,
            "turns": len([m for m in messages if m.type == "ai"]),
            "execution_time": execution_time,
            "messages": len(messages)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "execution_time": time.time() - start_time
        }

# ============================================================================
# CUSTOM IMPLEMENTATION (from test_litellm_agentic_loop.py)
# ============================================================================

# Register models with LiteLLM
litellm.register_model(model_cost={
    "ollama/qwen3:4b-instruct": {"supports_function_calling": True},
    "ollama/gemma3:4b": {"supports_function_calling": True},
})

# Tools in LiteLLM format
LITELLM_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Calculate a mathematical expression",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The mathematical expression to evaluate"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Timezone (e.g., UTC, EST, PST)",
                        "default": "UTC"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather information for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "final_answer",
            "description": "Return the final answer to the user. Call this when you have all needed information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "The final answer in natural language"
                    }
                },
                "required": ["answer"]
            }
        }
    }
]

def execute_tool_custom(tool_name: str, arguments: Dict) -> str:
    """Execute a tool for custom implementation"""
    if tool_name == "final_answer":
        return json.dumps({"ok": True, "answer": arguments.get("answer", "")})

    # Map to actual tool functions
    tool_map = {
        "calculate": lambda: calculate.invoke(arguments),
        "get_current_time": lambda: get_current_time.invoke(arguments),
        "get_weather": lambda: get_weather.invoke(arguments)
    }

    if tool_name not in tool_map:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        result = tool_map[tool_name]()
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": f"Error executing {tool_name}: {str(e)}"})

async def run_custom_agent(query: str, model: str, max_turns: int = 10) -> Dict:
    """Run query using custom agentic loop"""
    start_time = time.time()

    messages = [
        {
            "role": "system",
            "content": """You are a helpful assistant with access to tools.

When you have all the information needed, call final_answer with your complete response.
Do NOT call the same tool multiple times.
After getting tool results, immediately call final_answer."""
        },
        {"role": "user", "content": query}
    ]

    turns = 0

    for turn in range(max_turns):
        turns += 1

        response = await litellm.acompletion(
            model=model,
            messages=messages,
            tools=LITELLM_TOOLS,
            tool_choice="auto"
        )

        assistant_message = response.choices[0].message

        if assistant_message.tool_calls:
            messages.append(assistant_message.model_dump())

            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {}

                tool_result = execute_tool_custom(tool_name, tool_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })

                if tool_name == "final_answer":
                    return {
                        "success": True,
                        "answer": tool_args.get("answer", ""),
                        "turns": turns,
                        "execution_time": time.time() - start_time,
                        "messages": len(messages)
                    }
        else:
            # Assistant provided text response without tool call
            return {
                "success": True,
                "answer": assistant_message.content,
                "turns": turns,
                "execution_time": time.time() - start_time,
                "messages": len(messages)
            }

    return {
        "success": False,
        "error": "Max turns reached",
        "turns": turns,
        "execution_time": time.time() - start_time
    }

# ============================================================================
# TEST RUNNER AND COMPARISON
# ============================================================================

@dataclass
class TestResult:
    approach: str
    model: str
    query: str
    success: bool
    answer: str
    turns: int
    execution_time: float
    error: str = None

async def run_comparison(models: List[str], queries: List[str]):
    """Run comprehensive comparison between LangGraph and custom implementation"""

    results = []

    for model in models:
        model_display = model.replace("ollama/", "").replace(":4b-instruct", "").replace(":4b", "")

        print(f"\n{'='*80}")
        print(f"Testing: {model_display}")
        print(f"{'='*80}\n")

        for query in queries:
            print(f"Query: {query}")
            print("-" * 80)

            # Test 1: LangGraph
            print("  [LangGraph] Running...")
            lg_result = await run_langgraph_agent(query, model.replace("ollama/", ""))

            results.append(TestResult(
                approach="LangGraph",
                model=model_display,
                query=query,
                success=lg_result.get("success", False),
                answer=lg_result.get("answer", ""),
                turns=lg_result.get("turns", 0),
                execution_time=lg_result.get("execution_time", 0),
                error=lg_result.get("error")
            ))

            print(f"  [LangGraph] {'✅' if lg_result.get('success') else '❌'} "
                  f"Time: {lg_result.get('execution_time', 0):.2f}s "
                  f"Turns: {lg_result.get('turns', 0)}")

            # Test 2: Custom Implementation
            print("  [Custom] Running...")
            custom_result = await run_custom_agent(query, model)

            results.append(TestResult(
                approach="Custom",
                model=model_display,
                query=query,
                success=custom_result.get("success", False),
                answer=custom_result.get("answer", ""),
                turns=custom_result.get("turns", 0),
                execution_time=custom_result.get("execution_time", 0),
                error=custom_result.get("error")
            ))

            print(f"  [Custom] {'✅' if custom_result.get('success') else '❌'} "
                  f"Time: {custom_result.get('execution_time', 0):.2f}s "
                  f"Turns: {custom_result.get('turns', 0)}")
            print()

    return results

def print_comparison_table(results: List[TestResult]):
    """Print detailed comparison table"""
    print("\n" + "="*80)
    print("COMPARISON RESULTS")
    print("="*80)

    # Group by approach
    langgraph_results = [r for r in results if r.approach == "LangGraph"]
    custom_results = [r for r in results if r.approach == "Custom"]

    # Success rates
    print(f"\n{'Metric':<25} {'LangGraph':<20} {'Custom':<20}")
    print("-" * 80)

    lg_success = sum(1 for r in langgraph_results if r.success)
    custom_success = sum(1 for r in custom_results if r.success)

    print(f"{'Success Rate':<25} {lg_success}/{len(langgraph_results)} ({lg_success/len(langgraph_results)*100:.0f}%)"
          f"{'':>5} {custom_success}/{len(custom_results)} ({custom_success/len(custom_results)*100:.0f}%)")

    # Average metrics
    lg_avg_time = sum(r.execution_time for r in langgraph_results if r.success) / max(lg_success, 1)
    custom_avg_time = sum(r.execution_time for r in custom_results if r.success) / max(custom_success, 1)

    lg_avg_turns = sum(r.turns for r in langgraph_results if r.success) / max(lg_success, 1)
    custom_avg_turns = sum(r.turns for r in custom_results if r.success) / max(custom_success, 1)

    print(f"{'Avg Execution Time':<25} {lg_avg_time:.2f}s{'':>14} {custom_avg_time:.2f}s")
    print(f"{'Avg Turns':<25} {lg_avg_turns:.1f}{'':>16} {custom_avg_turns:.1f}")

    # Detailed results per query
    print("\n" + "="*80)
    print("DETAILED RESULTS BY QUERY")
    print("="*80)

    queries = list(set(r.query for r in results))
    for query in queries:
        print(f"\nQuery: {query}")
        print("-" * 80)

        lg = next((r for r in langgraph_results if r.query == query), None)
        custom = next((r for r in custom_results if r.query == query), None)

        if lg:
            status = "✅" if lg.success else f"❌ {lg.error}"
            print(f"  LangGraph: {status}")
            if lg.success:
                print(f"    Answer: {lg.answer[:100]}...")
                print(f"    Turns: {lg.turns}, Time: {lg.execution_time:.2f}s")

        if custom:
            status = "✅" if custom.success else f"❌ {custom.error}"
            print(f"  Custom:    {status}")
            if custom.success:
                print(f"    Answer: {custom.answer[:100]}...")
                print(f"    Turns: {custom.turns}, Time: {custom.execution_time:.2f}s")

# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run the comparison tests"""

    # Configuration
    MODELS = [
        "ollama/qwen3:4b-instruct",
        # "ollama/gemma3:4b",  # Uncomment to test Gemma too
    ]

    QUERIES = [
        "What is 25 * 4 + 10?",
        "What time is it?",
        "What's the weather in London?",
        "What time is it in London and what's the weather there?",
        "Calculate 50 + 50 and tell me the current time"
    ]

    print("\n" + "="*80)
    print("LangGraph vs Custom Agentic Loop - SLM Comparison")
    print("="*80)
    print(f"Models: {len(MODELS)}")
    print(f"Queries: {len(QUERIES)}")
    print(f"Total tests: {len(MODELS) * len(QUERIES) * 2}")  # 2 approaches

    # Run tests
    results = await run_comparison(MODELS, QUERIES)

    # Print comparison
    print_comparison_table(results)

    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    print("LangGraph Pros: Production-ready, less code, built-in features")
    print("Custom Pros: Full control, transparent, educational, fewer deps")
    print("\nBoth approaches work well with SLMs!")

if __name__ == "__main__":
    asyncio.run(main())
