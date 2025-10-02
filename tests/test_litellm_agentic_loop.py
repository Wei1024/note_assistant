#!/usr/bin/env python3
"""
Test LiteLLM with qwen3:4b-instruct in an agentic loop with tools
This tests if the model knows when to stop calling tools
"""

import asyncio
import json
import litellm
from datetime import datetime
from typing import List, Dict, Any

# Configure LiteLLM
import os
os.environ['LITELLM_LOG'] = 'INFO'

# Define tools
tools = [
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
    }
]

# Add final_answer tool for explicit termination
FINAL_TOOL = {
    "type": "function",
    "function": {
        "name": "final_answer",
        "description": "Return the final, natural-language answer for the user. Call this after you have gathered all necessary information from other tools.",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "The user-facing final reply, in natural language."
                }
            },
            "required": ["answer"]
        }
    }
}

# Add final_answer to the tools list
tools.append(FINAL_TOOL)

# Tool implementations
def calculate(expression: str = "") -> Dict:
    """Execute calculation"""
    if not expression:
        return {"error": "No expression provided"}
    try:
        result = eval(expression, {"__builtins__": {}})
        return {"expression": expression, "result": result}
    except Exception as e:
        return {"error": str(e)}

def get_current_time(timezone: str = "UTC") -> Dict:
    """Get current time"""
    now = datetime.now()
    return {
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "timezone": timezone
    }

def get_weather(city: str = "") -> Dict:
    """Get mock weather data"""
    if not city:
        return {"error": "No city provided"}
    weather_data = {
        "London": {"temp": "15°C", "condition": "Cloudy"},
        "Tokyo": {"temp": "22°C", "condition": "Sunny"},
        "New York": {"temp": "18°C", "condition": "Partly cloudy"},
    }
    return weather_data.get(city, {"temp": "20°C", "condition": "Clear"})

# Tool execution
def execute_tool(tool_name: str, arguments: Dict) -> str:
    """Execute a tool and return the result"""
    # Handle final_answer specially - it's a control flow tool, not a real tool
    if tool_name == "final_answer":
        return json.dumps({"ok": True, "answer": arguments.get("answer", "")})

    tool_map = {
        "calculate": calculate,
        "get_current_time": get_current_time,
        "get_weather": get_weather
    }

    if tool_name not in tool_map:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        # Let Python handle argument matching - it will raise TypeError if args don't match
        result = tool_map[tool_name](**arguments)
        return json.dumps(result)
    except TypeError as e:
        # Handle missing/extra arguments gracefully
        return json.dumps({"error": f"Invalid arguments for {tool_name}: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"Error executing {tool_name}: {str(e)}"})

# ReAct-style planning system for multi-tool scenarios
PLAN_SYSTEM = """You are planning tool use.
Return ONLY valid JSON matching this structure:
{
  "steps": [
    {"tool": "calculate|get_current_time|get_weather", "arguments": {...}, "why": "reason for this step"}
  ],
  "final_message": "Brief explanation of what you'll do"
}

Examples:

Query: "What's the weather in Tokyo?"
{
  "steps": [
    {"tool": "get_weather", "arguments": {"city": "Tokyo"}, "why": "Get weather information for Tokyo"}
  ],
  "final_message": "I'll get the current weather in Tokyo."
}

Query: "Calculate 100 + 50 and tell me what time it is"
{
  "steps": [
    {"tool": "calculate", "arguments": {"expression": "100 + 50"}, "why": "Calculate the sum"},
    {"tool": "get_current_time", "arguments": {"timezone": "UTC"}, "why": "Get the current time"}
  ],
  "final_message": "I'll calculate 100 + 50 and get the current time."
}

Query: "What's the time in London and the weather there?"
{
  "steps": [
    {"tool": "get_current_time", "arguments": {"timezone": "Europe/London"}, "why": "Get London time"},
    {"tool": "get_weather", "arguments": {"city": "London"}, "why": "Get London weather"}
  ],
  "final_message": "I'll get the current time and weather for London."
}

Rules:
- Include 1-3 steps maximum
- Each step must have: tool (name), arguments (dict), why (reason)
- Valid tools: calculate, get_current_time, get_weather
- Valid arguments:
  - calculate: {"expression": "math expression"}
  - get_current_time: {"timezone": "timezone name"} or {} for UTC
  - get_weather: {"city": "city name"}
- Do not execute tools, only plan
- Output ONLY the JSON, no other text"""

async def get_tool_plan(query: str, model: str):
    """Get a structured plan for tool usage"""
    messages = [
        {"role": "system", "content": PLAN_SYSTEM},
        {"role": "user", "content": f"User query: {query}\n\nPlan your steps as JSON."}
    ]

    print("\n📝 === PLANNING PHASE ===")
    print(f"   Query: {query}")

    try:
        # First attempt
        print("\n   🤖 First planning attempt...")
        resp = await litellm.acompletion(
            model=model,
            messages=messages,
            tools=[],  # No tools available during planning
            tool_choice="none",
            temperature=0.1,
            max_tokens=500
        )

        text = resp.choices[0].message.content.strip()
        print(f"   📄 AI Response (raw):\n   {'-'*40}")
        print(f"   {text}")
        print(f"   {'-'*40}")

        # Try to extract JSON from the response
        original_text = text
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        plan = json.loads(text)
        assert "steps" in plan and isinstance(plan["steps"], list)
        print(f"   ✅ Successfully parsed plan with {len(plan['steps'])} steps")
        return plan

    except Exception as e:
        print(f"   ❌ Parsing failed: {e}")
        print(f"   🔄 Attempting fallback with stricter instructions...")

        # Fallback: try once more with stricter instructions
        messages.append({
            "role": "assistant",
            "content": original_text
        })
        messages.append({
            "role": "user",
            "content": "Your output was not valid JSON. Output ONLY the JSON object, no markdown, no explanation."
        })

        print("\n   🤖 Second planning attempt (fallback)...")
        resp = await litellm.acompletion(
            model=model,
            messages=messages,
            tools=[],
            tool_choice="none",
            temperature=0.0,
            max_tokens=500
        )

        text = resp.choices[0].message.content.strip()
        print(f"   📄 AI Response (fallback):\n   {'-'*40}")
        print(f"   {text}")
        print(f"   {'-'*40}")

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        plan = json.loads(text.strip())
        print(f"   ✅ Fallback successful with {len(plan.get('steps', []))} steps")
        return plan

async def run_multi_tool(query: str, model: str):
    """Execute multi-tool queries using Plan → Execute → Synthesize approach"""
    print(f"\n🎯 Using ReAct multi-tool approach for: {query}")

    # Step 1: Get the plan
    try:
        plan = await get_tool_plan(query, model)
        steps = plan.get("steps", [])[:3]  # Limit to 3 steps max
        print(f"📋 Plan: {plan.get('final_message', 'Processing...')}")
        print(f"   Steps: {len(steps)}")
        for i, step in enumerate(steps, 1):
            print(f"   {i}. {step['tool']}: {step.get('why', '')}")
    except Exception as e:
        print(f"❌ Failed to create plan: {e}")
        return None

    # Step 2: Execute each planned step deterministically
    messages = [
        {
            "role": "system",
            "content": """You are reviewing tool results.
After reviewing ALL results, you MUST call final_answer with a complete natural-language response.
Do NOT call any other tools - just synthesize the results into a final answer."""
        },
        {"role": "user", "content": query}
    ]

    # Track what we've already executed to avoid duplicates
    executed = set()
    tool_results = []

    for i, step in enumerate(steps, 1):
        tool_name = step.get("tool")
        tool_args = step.get("arguments", {}) or {}

        # Create a unique key for deduplication
        exec_key = (tool_name, json.dumps(tool_args, sort_keys=True))
        if exec_key in executed:
            print(f"   ⏭️  Skipping duplicate: {tool_name}")
            continue
        executed.add(exec_key)

        # Execute the tool
        print(f"   ▶️  Executing {tool_name} with {tool_args}")
        result = execute_tool(tool_name, tool_args)
        tool_results.append({
            "tool": tool_name,
            "args": tool_args,
            "result": result
        })

    # Step 3: Synthesize results into final answer
    print("\n📊 === SYNTHESIS PHASE ===")

    # Build a summary of what was executed
    results_summary = "Tool execution results:\n"
    for tr in tool_results:
        results_summary += f"- {tr['tool']}: {tr['result']}\n"

    print(f"   📋 Tool Results Summary:")
    print(f"   {'-'*40}")
    print(f"   {results_summary}")
    print(f"   {'-'*40}")

    messages.append({
        "role": "assistant",
        "content": results_summary
    })
    messages.append({
        "role": "user",
        "content": "Now provide a final answer based on these results. Call final_answer with your response."
    })

    print("\n   🤖 Requesting final synthesis...")

    # Get final response with final_answer tool available
    resp = await litellm.acompletion(
        model=model,
        messages=messages,
        tools=[FINAL_TOOL],  # Only final_answer available
        tool_choice="required",
        temperature=0.2,
        max_tokens=400
    )

    # Extract final answer
    msg = resp.choices[0].message

    print(f"   📄 AI Response:")
    if msg.tool_calls:
        for tool_call in msg.tool_calls:
            print(f"   Tool Call: {tool_call.function.name}")
            print(f"   Arguments: {tool_call.function.arguments}")
            if tool_call.function.name == "final_answer":
                args = json.loads(tool_call.function.arguments)
                final_answer = args.get("answer", "")
                print(f"\n✅ Final answer: {final_answer}")
                return final_answer
    elif msg.content:
        print(f"   Content (no tool call): {msg.content}")
        print(f"\n✅ Final answer (fallback): {msg.content}")
        return msg.content

    print("   ❌ No final answer provided")
    return None

async def run_agentic_loop(query: str, model: str = "ollama/qwen3:4b-instruct", max_turns: int = 10, use_react: bool = False):
    """Run an agentic loop with tool calling

    Args:
        query: The user query
        model: The model to use
        max_turns: Maximum number of turns before giving up
        use_react: If True, use ReAct (Plan → Execute → Synthesize) approach
    """
    print(f"\nQuery: {query}")
    print("="*60)

    # Use ReAct approach if explicitly requested
    if use_react:
        print("🔄 Using ReAct approach")
        result = await run_multi_tool(query, model)
        if result:
            return result
        else:
            print("⚠️ ReAct approach failed, falling back to standard approach")

    # Initialize conversation with few-shot examples
    messages = [
        {
            "role": "system",
            "content": """You are a helpful assistant with access to tools.

CRITICAL INSTRUCTIONS:
1. You may call multiple utility tools as needed to gather all required information
2. When done gathering information, call exactly once: final_answer(answer=...)
3. Do not repeat final_answer
4. Do not return JSON to the user - only use final_answer for your response

IMPORTANT RULES:
1. Use tools to get accurate information
2. If a query requires multiple pieces of information, call all necessary tools
3. After receiving ALL needed tool results, you MUST call final_answer with your complete response
4. DO NOT call the same tool multiple times for the same query
5. Once you have all the information you need, immediately call final_answer

Here are examples of correct behavior:

Example 1:
User: What is 10 + 20?
Assistant: [Calls calculate tool with {"expression": "10 + 20"}]
Tool Result: {"result": 30}
Assistant: [Calls final_answer with {"answer": "The result of 10 + 20 is 30."}]

Example 2:
User: What time is it?
Assistant: [Calls get_current_time tool]
Tool Result: {"time": "14:30:00", "date": "2025-01-01"}
Assistant: [Calls final_answer with {"answer": "The current time is 14:30:00 on 2025-01-01."}]

Example 3 (Multiple tools):
User: What's the time and weather in London?
Assistant: [Calls get_current_time tool with {"timezone": "Europe/London"}]
Tool Result: {"time": "14:30:00", "date": "2025-01-01", "timezone": "Europe/London"}
Assistant: [Calls get_weather tool with {"city": "London"}]
Tool Result: {"temp": "15°C", "condition": "Cloudy"}
Assistant: [Calls final_answer with {"answer": "In London, it's 14:30:00 on 2025-01-01, and the weather is cloudy with 15°C."}]

NEVER do this (wrong):
User: What is 5 + 5?
Assistant: [Calls calculate tool]
Tool Result: {"result": 10}
Assistant: [Calls calculate tool again] ← WRONG! Should call final_answer instead
Tool Result: {"result": 10}
Assistant: The answer is 10. ← WRONG! Must call final_answer tool

Remember: After getting your result, always call final_answer to provide the answer."""
        },
        {
            "role": "user",
            "content": query
        }
    ]

    for turn in range(max_turns):
        print(f"\n--- Turn {turn + 1} ---")

        # Call LiteLLM
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        assistant_message = response.choices[0].message

        # Check if the assistant wants to use tools
        if assistant_message.tool_calls:
            print(f"Assistant wants to call tools:")
            messages.append(assistant_message.model_dump())

            # Execute each tool call
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {}
                print(f"  - Calling {tool_name} with {tool_args}")

                # Execute tool
                tool_result = execute_tool(tool_name, tool_args)
                print(f"  - Result: {tool_result}")

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })

                # Check if this is the final_answer tool
                if tool_name == "final_answer":
                    final_answer = tool_args.get("answer", "")
                    print(f"\n✅ Agent called final_answer with: {final_answer}")
                    print(f"Total turns: {turn + 1}")
                    return final_answer

            # If final_answer wasn't called, continue the loop
        else:
            # Assistant provided a final answer
            final_answer = assistant_message.content
            print(f"Assistant's final answer: {final_answer}")
            messages.append({"role": "assistant", "content": final_answer})

            print("\n✅ Agent stopped calling tools and provided final answer")
            print(f"Total turns: {turn + 1}")
            return final_answer

    print(f"\n❌ Max turns ({max_turns}) reached - agent didn't stop")
    print("\nConversation history:")
    for i, msg in enumerate(messages):
        role = msg.get("role", "")
        if role == "tool":
            print(f"  {i}. Tool result: {msg.get('content', '')[:100]}...")
        elif role == "assistant" and msg.get("tool_calls"):
            print(f"  {i}. Assistant: [Tool calls]")
        else:
            content = msg.get("content", "")
            if content:
                print(f"  {i}. {role}: {content[:100]}...")

    return None

async def main(models_config, test_queries):
    """Run tests with configured models and queries"""

    # Register all models with LiteLLM
    model_registration = {}
    for config in models_config:
        model_registration[f"ollama/{config['model_name']}"] = {
            "supports_function_calling": True
        }
    litellm.register_model(model_cost=model_registration)

    # Store results for summary
    all_results = {}

    for config in models_config:
        model_name = config["model_name"]
        model_path = f"ollama/{model_name}"

        print("\n" + "="*60)
        print(f"Testing {config['display_name']} with Few-Shot Examples")
        print("="*60)

        successes = 0
        results = []

        for query, use_react in test_queries:
            result = await run_agentic_loop(
                query,
                model=model_path,
                max_turns=config.get("max_turns", 5),
                use_react=use_react
            )

            if result:
                successes += 1
                results.append("✅")
            else:
                results.append("❌")
                print("⚠️ Agent failed to provide final answer\n")
            print("\n" + "-"*60)

        all_results[config['display_name']] = {
            'successes': successes,
            'total': len(test_queries),
            'results': results
        }
        print(f"\n{config['display_name']} Results: {successes}/{len(test_queries)} successful")

    # Print summary table
    print("\n" + "="*60)
    print("SUMMARY - Tool Calling Performance with Few-Shot Examples")
    print("="*60)

    # Print header
    print(f"\n{'Model':<25} {'Success Rate':<15} {'Results'}")
    print("-" * 60)

    # Print results for each model
    for model_name, data in all_results.items():
        success_rate = f"{data['successes']}/{data['total']} ({data['successes']/data['total']*100:.0f}%)"
        results_str = " ".join(data['results'])
        print(f"{model_name:<25} {success_rate:<15} {results_str}")

    print("\nLegend: ✅ = Success, ❌ = Failed (infinite loop)")
    print("\nFew-shot examples help models understand when to stop calling tools")

if __name__ == "__main__":
    # ========================================================
    # CONFIGURATION - Easy to modify for testing new models
    # ========================================================

    # Add or remove models here - just update this list!
    MODELS_TO_TEST = [
        {
            "model_name": "gemma3:4b",        # Actual model name in Ollama
            "display_name": "Gemma 3 (4B)",   # Pretty name for display
            "max_turns": 5                     # Max turns before giving up
        },
        {
            "model_name": "qwen3:4b-instruct",
            "display_name": "Qwen 3 (4B)",
            "max_turns": 5
        },
        # {
        #     "model_name": "qwen3:8b",        # Actual model name in Ollama
        #     "display_name": "Qwen 3 (8B)",   # Pretty name for display
        #     "max_turns": 5                     # Max turns before giving up
        # },
        # Add more models here:
        # {
        #     "model_name": "llama3.2",
        #     "display_name": "Llama 3.2",
        #     "max_turns": 5
        # },
        # {
        #     "model_name": "mistral",
        #     "display_name": "Mistral 7B",
        #     "max_turns": 5
        # },
    ]

    # Test queries - can be modified as needed
    # Format: (query, use_react)
    TEST_QUERIES = [
        ("What is 25 * 4 + 10?", False),
        ("What time is it?", False),
        ("What's the weather in London?", False),
        ("What time is it in London and what's the weather there?", True),  # Multi-tool: use ReAct
        ("Calculate 50 + 50 and tell me the current time", True)  # Multi-tool: use ReAct
    ]

    # Run the tests
    asyncio.run(main(MODELS_TO_TEST, TEST_QUERIES))