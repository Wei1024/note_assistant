#!/usr/bin/env python3
"""
Test OpenAI GPT-5 with LiteLLM and OpenAI Agents SDK
This confirms the integration works properly with a model that supports tool calling
"""

import asyncio
import os
from datetime import datetime
from typing import Dict
import agentops
from agents import Agent, Runner, function_tool, ModelSettings
from agents.extensions.models.litellm_model import LitellmModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize AgentOps
agentops_api_key = os.getenv('AGENTOPS_API_KEY')
if agentops_api_key:
    agentops.init(api_key=agentops_api_key)
    print("✅ AgentOps initialized with API key")
else:
    agentops.init()
    print("⚠️  AgentOps initialized without API key (local mode)")

# Get OpenAI API key
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    print("❌ OPENAI_API_KEY not found in environment")
    exit(1)
else:
    print("✅ OpenAI API key loaded")

# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

@function_tool
def calculate(expression: str) -> Dict:
    """
    Calculate a mathematical expression.

    Args:
        expression: Math expression to evaluate

    Returns:
        Dictionary with calculation result
    """
    try:
        result = eval(expression, {"__builtins__": {}})
        return {
            "expression": expression,
            "result": result,
            "type": type(result).__name__
        }
    except Exception as e:
        return {"error": f"Failed to calculate: {str(e)}"}

@function_tool
def get_current_time(timezone_name: str = "UTC") -> Dict:
    """
    Get the current date and time.

    Args:
        timezone_name: Timezone name (e.g., "UTC", "EST", "PST")

    Returns:
        Dictionary with current time information
    """
    from datetime import timezone as tz
    now = datetime.now(tz.utc)
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timezone": timezone_name,
        "timestamp": now.isoformat(),
        "day_of_week": now.strftime("%A")
    }

@function_tool
def get_weather(city: str) -> Dict:
    """
    Get weather information for a city (mock data for testing).

    Args:
        city: City name

    Returns:
        Dictionary with weather information
    """
    # Mock weather data
    weather_data = {
        "London": {"temp": "15°C", "condition": "Cloudy", "humidity": "70%"},
        "Tokyo": {"temp": "22°C", "condition": "Sunny", "humidity": "55%"},
        "New York": {"temp": "18°C", "condition": "Partly cloudy", "humidity": "60%"},
        "Paris": {"temp": "17°C", "condition": "Rainy", "humidity": "80%"},
    }

    data = weather_data.get(city, {"temp": "20°C", "condition": "Clear", "humidity": "50%"})
    return {
        "city": city,
        "temperature": data["temp"],
        "condition": data["condition"],
        "humidity": data["humidity"],
        "wind": "10 km/h"
    }

# ============================================================================
# TEST SCENARIOS
# ============================================================================

async def test_gpt5_single_tool():
    """Test GPT-5 with single tool calls"""
    print("\n" + "="*60)
    print("TEST 1: GPT-5 Single Tool Calls")
    print("="*60)

    # Create LiteLLM model for GPT-5
    litellm_model = LitellmModel(
        model="gpt-5",  # Using GPT-5
        api_key=openai_api_key
    )

    # Create agent
    agent = Agent(
        name="Assistant",
        instructions="""You are a helpful AI assistant with access to various tools.
        Use the appropriate tools to answer user questions accurately.""",
        model=litellm_model,
        tools=[get_current_time, calculate, get_weather],
        model_settings=ModelSettings(include_usage=True)
    )

    test_queries = [
        "What is 25 * 4 + 10?",
        "What time is it?",
        "What's the weather in Tokyo?"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)

        session = agentops.start_session(tags={
            "test": "gpt5_single_tool",
            "model": "gpt-5"
        })

        try:
            result = await Runner.run(
                starting_agent=agent,
                input=query,
                max_turns=5  # Should only need 2-3 turns
            )
            print(f"✅ Response: {result.final_output}")

            if hasattr(result, 'usage'):
                print(f"Usage: {result.usage}")

            agentops.end_session(session)
        except Exception as e:
            print(f"❌ Error: {e}")
            agentops.end_session(session, error=str(e))

async def test_gpt5_multi_tool():
    """Test GPT-5 with multiple tools in one query"""
    print("\n" + "="*60)
    print("TEST 2: GPT-5 Multi-Tool Query")
    print("="*60)

    # Create LiteLLM model for GPT-5
    litellm_model = LitellmModel(
        model="gpt-5",
        api_key=openai_api_key
    )

    # Create agent
    agent = Agent(
        name="Multi-Tool Assistant",
        instructions="""You are a helpful assistant with multiple capabilities.
        When asked complex questions, use multiple tools to provide comprehensive answers.""",
        model=litellm_model,
        tools=[get_current_time, calculate, get_weather],
        model_settings=ModelSettings(include_usage=True)
    )

    complex_query = "What's the current time, the weather in London, and what's 15% of 200?"

    print(f"Query: {complex_query}")
    print("-" * 40)

    session = agentops.start_session(tags={
        "test": "gpt5_multi_tool",
        "model": "gpt-5"
    })

    try:
        result = await Runner.run(
            starting_agent=agent,
            input=complex_query,
            max_turns=5
        )
        print(f"✅ Response: {result.final_output}")

        if hasattr(result, 'usage'):
            print(f"Usage: {result.usage}")

        agentops.end_session(session)
    except Exception as e:
        print(f"❌ Error: {e}")
        agentops.end_session(session, error=str(e))

async def test_comparison_with_ollama_models():
    """Compare GPT-5 with qwen3:4b-instruct and gemma3:4b"""
    print("\n" + "="*60)
    print("TEST 3: Comparison - GPT-5 vs qwen3 vs gemma3")
    print("="*60)

    query = "Calculate 50 + 50"

    # Test with GPT-5
    print("\n--- Testing with GPT-5 ---")
    gpt5_model = LitellmModel(
        model="gpt-5",
        api_key=openai_api_key
    )

    gpt5_agent = Agent(
        name="GPT-5 Assistant",
        instructions="You are a helpful assistant. Use the calculate tool for math questions.",
        model=gpt5_model,
        tools=[calculate]
    )

    try:
        result = await Runner.run(
            starting_agent=gpt5_agent,
            input=query,
            max_turns=5
        )
        print(f"✅ GPT-5 succeeded: {result.final_output}")
    except Exception as e:
        print(f"❌ GPT-5 failed: {e}")

    # Test with gemma3:4b
    print("\n--- Testing with gemma3:4b ---")
    gemma_model = LitellmModel(
        model="ollama/gemma3:4b",
        api_key="dummy"
    )

    gemma_agent = Agent(
        name="Gemma Assistant",
        instructions="""You are a helpful assistant. Use the calculate tool for math questions.

        IMPORTANT: After receiving the tool result, immediately provide a final answer to the user.
        Format your response in natural language, not raw JSON.""",
        model=gemma_model,
        tools=[calculate]
    )

    try:
        result = await Runner.run(
            starting_agent=gemma_agent,
            input=query,
            max_turns=5  # Give it more turns since it might need them
        )
        print(f"✅ Gemma succeeded: {result.final_output}")
    except Exception as e:
        print(f"❌ Gemma failed: {e}")

    # Test with qwen3:4b-instruct
    print("\n--- Testing with qwen3:4b-instruct ---")
    qwen_model = LitellmModel(
        model="ollama/qwen3:4b-instruct",
        api_key="dummy"
    )

    qwen_agent = Agent(
        name="Qwen Assistant",
        instructions="You are a helpful assistant. Use the calculate tool for math questions.",
        model=qwen_model,
        tools=[calculate]
    )

    try:
        result = await Runner.run(
            starting_agent=qwen_agent,
            input=query,
            max_turns=3
        )
        print(f"✅ Qwen succeeded: {result.final_output}")
    except Exception as e:
        print(f"❌ Qwen failed: {e}")

# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("OpenAI GPT-5 + LiteLLM + OpenAI Agents SDK Test")
    print("="*60)

    # Run tests
    await test_gpt5_single_tool()
    await test_gpt5_multi_tool()
    await test_comparison_with_ollama_models()

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("✅ Tests completed")
    print("📊 Check AgentOps dashboard for traces")
    print("\nExpected results:")
    print("- GPT-5: Should stop immediately after tool result and provide final answer")
    print("- gemma3:4b: Might call tools 2-3 times but should eventually stop")
    print("- qwen3:4b-instruct: Will likely hit max turns (infinite tool calling loop)")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        agentops.end_all_sessions()
        print("\n🔚 All AgentOps sessions ended")