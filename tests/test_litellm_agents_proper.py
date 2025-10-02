#!/usr/bin/env python3
"""
Proper integration of OpenAI Agents SDK with LiteLLM for Ollama
Using the official LitellmModel extension
"""

import asyncio
import os
from datetime import datetime, timezone
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

# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

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
def calculate(expression: str) -> Dict:
    """
    Safely evaluate a mathematical expression.

    Args:
        expression: Mathematical expression to evaluate

    Returns:
        Dictionary with calculation result
    """
    try:
        # Safe evaluation
        result = eval(expression, {"__builtins__": {}})
        return {
            "expression": expression,
            "result": result,
            "type": type(result).__name__
        }
    except Exception as e:
        return {"error": f"Failed to calculate: {str(e)}"}

@function_tool
def get_weather(city: str) -> Dict:
    """
    Get weather information for a city (mock data for testing).

    Args:
        city: City name

    Returns:
        Dictionary with weather information
    """
    # Mock weather data for testing
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
        "wind": "10 km/h",
        "observation_time": datetime.utcnow().isoformat()
    }

# ============================================================================
# TEST SCENARIOS
# ============================================================================

async def test_single_agent_with_tools():
    """Test a single agent with multiple tools using LiteLLM"""
    print("\n" + "="*60)
    print("TEST 1: Single Agent with Tools (via LiteLLM)")
    print("="*60)

    # Create LiteLLM model for Ollama
    # For Ollama, we don't need an API key, but LiteLLM might require a dummy one
    litellm_model = LitellmModel(
        model="ollama/qwen3:4b-instruct",
        api_key="dummy"  # Ollama doesn't use API keys
    )

    # Create agent with LiteLLM model
    agent = Agent(
        name="Assistant",
        instructions="""You are a helpful AI assistant with access to various tools.
        You can tell time, perform calculations, and check weather.
        Use the appropriate tools to answer user questions accurately.

        IMPORTANT: After you receive a tool result, immediately provide a final answer to the user.
        Do NOT call the same tool again. Use the tool result to formulate your response and stop.""",
        model=litellm_model,
        tools=[get_current_time, calculate, get_weather],
        model_settings=ModelSettings(include_usage=True)  # Track usage
    )

    test_queries = [
        "What time is it?",
        "Calculate 25 * 4 + 10",
        "What's the weather in Tokyo?"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)

        session = agentops.start_session(tags={
            "test": "single_agent",
            "model": "ollama/qwen3:4b-instruct"
        })

        try:
            result = await Runner.run(
                starting_agent=agent,
                input=query
            )
            print(f"Response: {result.final_output}")

            # Check if usage info is available
            if hasattr(result, 'usage'):
                print(f"Usage: {result.usage}")

            agentops.end_session(session)
        except Exception as e:
            print(f"Error: {e}")
            agentops.end_session(session, error=str(e))

async def test_multi_agent_handoff():
    """Test multiple agents with handoffs using LiteLLM"""
    print("\n" + "="*60)
    print("TEST 2: Multi-Agent Handoff (via LiteLLM)")
    print("="*60)

    # Create LiteLLM model
    litellm_model = LitellmModel(
        model="ollama/qwen3:4b-instruct",
        api_key="dummy"
    )

    # Create specialized agents
    math_agent = Agent(
        name="Math Expert",
        instructions="""You are a mathematics expert.
        You can solve complex calculations and explain mathematical concepts.
        Use the calculate tool to verify your answers.

        IMPORTANT: After receiving the tool result, provide the final answer immediately.
        Do NOT call the tool again for the same calculation.""",
        model=litellm_model,
        tools=[calculate]
    )

    info_agent = Agent(
        name="Info Agent",
        instructions="""You provide information about time and weather.
        Use the available tools to give accurate, current information.

        IMPORTANT: After receiving the tool result, provide the final answer immediately.
        Do NOT call the tool again for the same request.""",
        model=litellm_model,
        tools=[get_current_time, get_weather]
    )

    # Create router agent with handoffs
    router = Agent(
        name="Router",
        instructions="""You are a router that directs queries to the right specialist:
        - Send math questions to 'Math Expert'
        - Send time/weather questions to 'Info Agent'
        Choose the appropriate specialist based on the user's question.""",
        model=litellm_model,
        handoffs=[math_agent, info_agent]
    )

    test_queries = [
        "What's 123 * 45?",
        "What time is it in UTC?",
        "What's the weather in Paris?"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)

        session = agentops.start_session(tags={
            "test": "multi_agent",
            "model": "ollama/qwen3:4b-instruct"
        })

        try:
            result = await Runner.run(
                starting_agent=router,
                input=query
            )
            print(f"Response: {result.final_output}")
            agentops.end_session(session)
        except Exception as e:
            print(f"Error: {e}")
            agentops.end_session(session, error=str(e))

async def test_complex_query():
    """Test a complex query requiring multiple tools"""
    print("\n" + "="*60)
    print("TEST 3: Complex Multi-Tool Query (via LiteLLM)")
    print("="*60)

    # Create LiteLLM model
    litellm_model = LitellmModel(
        model="ollama/qwen3:4b-instruct",
        api_key="dummy"
    )

    # Create agent with all tools
    agent = Agent(
        name="Multi-Tool Assistant",
        instructions="""You are a helpful assistant with multiple capabilities.
        When asked complex questions, use multiple tools to provide comprehensive answers.
        Always use tools to get accurate information.

        IMPORTANT: After receiving tool results, compile them into a final answer.
        Do NOT call the same tool multiple times. Once you have all needed information, provide a complete response.""",
        model=litellm_model,
        tools=[get_current_time, calculate, get_weather],
        model_settings=ModelSettings(include_usage=True)
    )

    complex_query = "What's the current time, the weather in London, and what's 15% of 200?"

    print(f"Query: {complex_query}")
    print("-" * 40)

    session = agentops.start_session(tags={
        "test": "complex",
        "model": "ollama/qwen3:4b-instruct"
    })

    try:
        result = await Runner.run(
            starting_agent=agent,
            input=complex_query
        )
        print(f"Response: {result.final_output}")
        agentops.end_session(session)
    except Exception as e:
        print(f"Error: {e}")
        agentops.end_session(session, error=str(e))

# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("OpenAI Agents SDK + LiteLLM + Ollama Integration")
    print("Using official LitellmModel extension")
    print("Model: qwen3:4b-instruct (via Ollama)")
    print("="*60)

    # Check if Ollama is running
    import requests
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=2)
        if response.status_code == 200:
            print("✅ Ollama is running")
        else:
            print("⚠️  Ollama might not be running properly")
    except:
        print("❌ Ollama is not running. Please start it with: ollama serve")
        return

    # Run tests
    await test_single_agent_with_tools()
    await test_multi_agent_handoff()
    await test_complex_query()

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("✅ Integration test completed")
    print("📊 Check AgentOps dashboard for detailed traces")
    print("🔧 Stack: OpenAI Agents SDK → LitellmModel → LiteLLM → Ollama")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        agentops.end_all_sessions()
        print("\n🔚 All AgentOps sessions ended")