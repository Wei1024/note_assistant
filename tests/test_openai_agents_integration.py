#!/usr/bin/env python3
"""
Test OpenAI Agents SDK with Ollama + LiteLLM + AgentOps
Demonstrates multi-agent system with real tools and handoffs
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
import requests
import agentops
import litellm
from agents import Agent, Runner, function_tool
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure OpenAI SDK to use Ollama
# This makes the OpenAI Agents SDK use Ollama's OpenAI-compatible API
os.environ['OPENAI_BASE_URL'] = 'http://localhost:11434/v1'
os.environ['OPENAI_API_KEY'] = 'ollama'  # Required but not used by Ollama

# Initialize AgentOps for tracing
# Get API key from environment or use default behavior
agentops_api_key = os.getenv('AGENTOPS_API_KEY')
if agentops_api_key:
    agentops.init(api_key=agentops_api_key)
    print("✅ AgentOps initialized with API key")
else:
    # Initialize without API key - will work locally but won't send data to dashboard
    agentops.init()
    print("⚠️  AgentOps initialized without API key (local mode)")
    print("   To enable full tracing, sign up at https://agentops.ai and set AGENTOPS_API_KEY")

print("✅ Configured to use Ollama at http://localhost:11434/v1")

# ============================================================================
# REAL TOOLS DEFINITION
# ============================================================================

@function_tool
def get_current_time(timezone: Optional[str] = "UTC") -> Dict:
    """
    Get the current date and time.

    Args:
        timezone: Timezone name (e.g., "UTC", "EST", "PST"). Defaults to UTC.

    Returns:
        Dictionary with current time information
    """
    try:
        if timezone and timezone != "UTC":
            # For simplicity, we'll just use UTC with offset notation
            tz_offsets = {
                "EST": -5, "PST": -8, "CST": -6, "MST": -7,
                "CET": 1, "JST": 9, "AEST": 10
            }
            offset = tz_offsets.get(timezone, 0)
            note = f" (UTC{offset:+d})" if offset else ""
        else:
            note = ""

        now = datetime.now(timezone.utc)
        return {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timezone": f"{timezone}{note}",
            "timestamp": now.isoformat(),
            "day_of_week": now.strftime("%A")
        }
    except Exception as e:
        return {"error": str(e)}

@function_tool
def get_weather(city: str, country_code: Optional[str] = None) -> Dict:
    """
    Get current weather for a city using OpenWeatherMap API.

    Args:
        city: City name (e.g., "London", "New York")
        country_code: Optional 2-letter country code (e.g., "GB", "US")

    Returns:
        Dictionary with weather information
    """
    # Using wttr.in as a free weather API (no key needed)
    try:
        location = f"{city},{country_code}" if country_code else city
        url = f"https://wttr.in/{location}?format=j1"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            current = data["current_condition"][0]
            return {
                "location": location,
                "temperature_c": current["temp_C"],
                "temperature_f": current["temp_F"],
                "condition": current["weatherDesc"][0]["value"],
                "humidity": f"{current['humidity']}%",
                "wind_speed": f"{current['windspeedKmph']} km/h",
                "feels_like_c": current["FeelsLikeC"],
                "observation_time": current["localObsDateTime"]
            }
        else:
            return {"error": f"Weather service returned status {response.status_code}"}
    except Exception as e:
        return {"error": f"Failed to fetch weather: {str(e)}"}

@function_tool
def calculate_expression(expression: str) -> Dict:
    """
    Safely evaluate a mathematical expression.

    Args:
        expression: Mathematical expression to evaluate (e.g., "2+2*3", "sqrt(16)")

    Returns:
        Dictionary with calculation result
    """
    import math
    import re

    try:
        # Remove dangerous characters/functions
        if re.search(r'[^0-9+\-*/().\s]|import|exec|eval|open|file|input|raw_input|compile', expression):
            # Allow specific math functions
            allowed_funcs = ['sqrt', 'sin', 'cos', 'tan', 'log', 'exp', 'pow', 'abs']
            safe_expr = expression
            for func in allowed_funcs:
                safe_expr = safe_expr.replace(func, f'math.{func}')

            # Create safe namespace with math functions
            safe_dict = {
                'math': math,
                '__builtins__': {}
            }

            result = eval(safe_expr, safe_dict)
        else:
            result = eval(expression, {"__builtins__": {}})

        return {
            "expression": expression,
            "result": result,
            "type": type(result).__name__
        }
    except Exception as e:
        return {"error": f"Failed to calculate: {str(e)}"}

@function_tool
def search_news(query: str, language: str = "en") -> Dict:
    """
    Search for recent news articles about a topic.

    Args:
        query: Search query
        language: Language code (e.g., "en", "es", "fr")

    Returns:
        Dictionary with news results
    """
    # Using NewsAPI.org free tier (would need API key in production)
    # For demo, we'll use a mock response
    try:
        # In production, you'd use:
        # url = f"https://newsapi.org/v2/everything?q={query}&language={language}&apiKey=YOUR_KEY"

        # Mock response for demonstration
        return {
            "query": query,
            "language": language,
            "articles": [
                {
                    "title": f"Latest developments in {query}",
                    "description": f"Recent news and updates about {query}",
                    "source": "Demo News Network",
                    "published_at": datetime.now().isoformat()
                },
                {
                    "title": f"Expert analysis: Understanding {query}",
                    "description": f"In-depth coverage and analysis of {query} trends",
                    "source": "Tech Weekly",
                    "published_at": datetime.now().isoformat()
                }
            ],
            "total_results": 2,
            "status": "ok"
        }
    except Exception as e:
        return {"error": str(e)}

@function_tool
def convert_units(value: float, from_unit: str, to_unit: str) -> Dict:
    """
    Convert between common units.

    Args:
        value: Numeric value to convert
        from_unit: Source unit (e.g., "km", "miles", "celsius", "fahrenheit", "kg", "pounds")
        to_unit: Target unit

    Returns:
        Dictionary with conversion result
    """
    conversions = {
        # Length
        ("km", "miles"): lambda x: x * 0.621371,
        ("miles", "km"): lambda x: x * 1.60934,
        ("m", "ft"): lambda x: x * 3.28084,
        ("ft", "m"): lambda x: x / 3.28084,

        # Temperature
        ("celsius", "fahrenheit"): lambda x: (x * 9/5) + 32,
        ("fahrenheit", "celsius"): lambda x: (x - 32) * 5/9,

        # Weight
        ("kg", "pounds"): lambda x: x * 2.20462,
        ("pounds", "kg"): lambda x: x / 2.20462,

        # Volume
        ("liters", "gallons"): lambda x: x * 0.264172,
        ("gallons", "liters"): lambda x: x / 0.264172,
    }

    key = (from_unit.lower(), to_unit.lower())
    if key in conversions:
        result = conversions[key](value)
        return {
            "original": {"value": value, "unit": from_unit},
            "converted": {"value": round(result, 4), "unit": to_unit},
            "formula": f"{value} {from_unit} = {round(result, 4)} {to_unit}"
        }
    else:
        return {"error": f"Conversion from {from_unit} to {to_unit} not supported"}

# ============================================================================
# STRUCTURED OUTPUT MODELS
# ============================================================================

class TaskAnalysis(BaseModel):
    """Analysis of what the user is asking for"""
    task_type: str = Field(description="Type of task: weather, time, calculation, news, conversion, general")
    requires_tools: bool = Field(description="Whether this task requires tool usage")
    suggested_agent: str = Field(description="Which specialist agent should handle this")
    confidence: float = Field(description="Confidence score 0-1")

class InformationSummary(BaseModel):
    """Summary of information gathered"""
    main_points: List[str] = Field(description="Key points from the information")
    source: str = Field(description="Where the information came from")
    reliability: str = Field(description="How reliable is this information: high, medium, low")

# ============================================================================
# AGENT DEFINITIONS
# ============================================================================

def create_router_agent() -> Agent:
    """Create the main router agent that delegates to specialists"""
    return Agent(
        name="Router",
        instructions="""You are the main router agent. Your job is to:
        1. Understand what the user is asking for
        2. Determine which specialist agent should handle it
        3. Hand off to the appropriate specialist

        Available specialists:
        - Time Assistant: For date, time, and timezone queries
        - Weather Assistant: For weather and climate information
        - Calculator: For mathematical calculations
        - News Researcher: For current events and news
        - Unit Converter: For unit conversions

        Always be polite and explain what you're doing.""",
        handoffs=[]  # Will be set after creating other agents
    )

def create_time_agent() -> Agent:
    """Create agent specialized in time/date information"""
    return Agent(
        name="Time Assistant",
        instructions="""You are a time and date specialist. You can:
        - Tell the current time in any timezone
        - Provide date information
        - Calculate time differences

        Use the get_current_time tool to fetch accurate time information.
        Always specify the timezone when reporting times.""",
        tools=[get_current_time]
    )

def create_weather_agent() -> Agent:
    """Create agent specialized in weather information"""
    return Agent(
        name="Weather Assistant",
        instructions="""You are a weather information specialist. You can:
        - Get current weather for any city
        - Provide temperature, humidity, and conditions
        - Suggest weather-appropriate recommendations

        Use the get_weather tool to fetch weather data.
        Always include both Celsius and Fahrenheit when reporting temperatures.""",
        tools=[get_weather]
    )

def create_calculator_agent() -> Agent:
    """Create agent specialized in calculations"""
    return Agent(
        name="Calculator",
        instructions="""You are a mathematical calculator assistant. You can:
        - Evaluate mathematical expressions
        - Solve equations
        - Perform complex calculations including trigonometry

        Use the calculate_expression tool for all calculations.
        Always show the expression and result clearly.""",
        tools=[calculate_expression]
    )

def create_news_agent() -> Agent:
    """Create agent specialized in news/information research"""
    return Agent(
        name="News Researcher",
        instructions="""You are a news and information researcher. You can:
        - Search for recent news on any topic
        - Provide summaries of current events
        - Find information about trends and developments

        Use the search_news tool to find information.
        Always mention the source and date of information.""",
        tools=[search_news],
        output_type=InformationSummary
    )

def create_converter_agent() -> Agent:
    """Create agent specialized in unit conversions"""
    return Agent(
        name="Unit Converter",
        instructions="""You are a unit conversion specialist. You can convert between:
        - Length units (km, miles, meters, feet)
        - Temperature (Celsius, Fahrenheit)
        - Weight (kg, pounds)
        - Volume (liters, gallons)

        Use the convert_units tool for conversions.
        Always show both original and converted values.""",
        tools=[convert_units]
    )

# ============================================================================
# TEST SCENARIOS
# ============================================================================

async def test_single_agent(query: str, agent: Agent):
    """Test a single agent with a query"""
    print(f"\n{'='*60}")
    print(f"Testing Agent: {agent.name}")
    print(f"Query: {query}")
    print(f"{'='*60}")

    # Start AgentOps session
    session = agentops.start_session(tags={
        "test": "single_agent",
        "agent": agent.name,
        "model": "qwen3:4b-instruct"
    })

    try:
        # Configure the agent with the model (Ollama model name)
        agent.model = "qwen3:4b-instruct"

        # Run the agent (no model_client needed - it will use LiteLLM internally)
        result = await Runner.run(
            starting_agent=agent,
            input=query
        )

        print(f"\nResult: {result.final_output}")

        # End session successfully
        agentops.end_session(session)

    except Exception as e:
        print(f"Error: {e}")
        agentops.end_session(session, error=str(e))

async def test_multi_agent_handoff():
    """Test multi-agent system with handoffs"""
    print("\n" + "="*60)
    print("Testing Multi-Agent System with Handoffs")
    print("="*60)

    # Create all specialist agents
    time_agent = create_time_agent()
    weather_agent = create_weather_agent()
    calc_agent = create_calculator_agent()
    news_agent = create_news_agent()
    converter_agent = create_converter_agent()

    # Create router with handoffs to specialists
    router = Agent(
        name="Router",
        instructions="""You are the main router agent. Analyze the user's request and hand off to the appropriate specialist:
        - 'Time Assistant' for date/time queries
        - 'Weather Assistant' for weather information
        - 'Calculator' for math problems
        - 'News Researcher' for current events
        - 'Unit Converter' for unit conversions

        Be helpful and explain which assistant you're connecting them to.""",
        handoffs=[time_agent, weather_agent, calc_agent, news_agent, converter_agent],
        model="qwen3:4b-instruct"  # Set model here
    )

    # Set model for all specialist agents
    for agent in [time_agent, weather_agent, calc_agent, news_agent, converter_agent]:
        agent.model = "qwen3:4b-instruct"

    # Test queries that should trigger different agents
    test_queries = [
        "What time is it in Tokyo?",
        "What's the weather like in Paris?",
        "Calculate the square root of 144",
        "Convert 100 kilometers to miles",
        "Find news about artificial intelligence"
    ]

    for query in test_queries:
        print(f"\n{'-'*40}")
        print(f"Query: {query}")
        print(f"{'-'*40}")

        session = agentops.start_session(tags={
            "test": "multi_agent",
            "model": "qwen3:4b-instruct"
        })

        try:
            result = await Runner.run(
                starting_agent=router,
                input=query
            )

            print(f"Result: {result.final_output}")
            agentops.end_session(session)

        except Exception as e:
            print(f"Error: {e}")
            agentops.end_session(session, error=str(e))

async def test_tool_chaining():
    """Test an agent using multiple tools in sequence"""
    print("\n" + "="*60)
    print("Testing Tool Chaining")
    print("="*60)

    # Create an agent with multiple tools
    multi_tool_agent = Agent(
        name="Multi-Tool Assistant",
        instructions="""You are a helpful assistant with multiple capabilities.
        When asked complex questions, use multiple tools to provide comprehensive answers.
        For example, if asked about weather and time, use both tools.""",
        tools=[get_current_time, get_weather, calculate_expression, convert_units],
        model="qwen3:4b-instruct"  # Set model here
    )

    complex_query = "What's the weather in London and what time is it there? Also, if it's 20 celsius, what is that in fahrenheit?"

    session = agentops.start_session(tags={
        "test": "tool_chaining",
        "model": "qwen3:4b-instruct"
    })

    try:
        result = await Runner.run(
            starting_agent=multi_tool_agent,
            input=complex_query
        )

        print(f"Query: {complex_query}")
        print(f"Result: {result.final_output}")
        agentops.end_session(session)

    except Exception as e:
        print(f"Error: {e}")
        agentops.end_session(session, error=str(e))

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("OpenAI Agents SDK Integration Test")
    print("Stack: OpenAI Agents SDK + LiteLLM + Ollama + AgentOps")
    print("Model: qwen3:4b-instruct")
    print("="*60)

    # Test 1: Single agent with tools
    print("\n\n[TEST 1: SINGLE AGENT WITH TOOLS]")
    weather_agent = create_weather_agent()
    await test_single_agent("What's the weather in New York?", weather_agent)

    # Test 2: Multi-agent with handoffs
    print("\n\n[TEST 2: MULTI-AGENT SYSTEM WITH HANDOFFS]")
    await test_multi_agent_handoff()

    # Test 3: Tool chaining
    print("\n\n[TEST 3: TOOL CHAINING]")
    await test_tool_chaining()

    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print("✅ Tests completed")
    print("📊 Check AgentOps dashboard for traces")
    print("💡 All agents used Ollama via LiteLLM successfully")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        # Ensure all AgentOps sessions are closed
        agentops.end_all_sessions()
        print("\n🔚 All AgentOps sessions ended")