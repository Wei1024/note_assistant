#!/usr/bin/env python3
"""
Simple test following architecture_example.py pattern
Using LiteLLM with OpenAI Agents SDK
"""

import asyncio
import os
import litellm
import agentops
from agents import Agent, Runner, function_tool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize AgentOps
agentops.init()

# Configure LiteLLM
os.environ['LITELLM_LOG'] = 'INFO'

# Set the model globally for LiteLLM
litellm.model = "ollama/qwen3:4b-instruct"

# Register the model with function calling support
litellm.register_model(model_cost={
    "ollama/qwen3:4b-instruct": {
        "supports_function_calling": True
    },
})

# Simple test tools
@function_tool
def get_time() -> str:
    """Get the current time."""
    from datetime import datetime
    return f"The current time is {datetime.now().strftime('%H:%M:%S')}"

@function_tool
def calculate(expression: str) -> str:
    """Calculate a mathematical expression."""
    try:
        result = eval(expression, {"__builtins__": {}})
        return f"{expression} = {result}"
    except Exception as e:
        return f"Error: {e}"

async def test_basic():
    """Test basic agent with tools following architecture_example pattern"""
    print("\n" + "="*60)
    print("Testing Basic Agent with LiteLLM")
    print(f"Model: {litellm.model}")
    print("="*60)

    # Create agent WITHOUT specifying model (like architecture_example.py)
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant. Use the tools to answer questions.",
        tools=[get_time, calculate]
    )

    test_queries = [
        "What time is it?",
        "Calculate 25 + 17"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)

        # Start AgentOps session
        session = agentops.start_session(tags={
            "model": litellm.model,
            "test": "basic"
        })

        try:
            # Run the agent (same pattern as architecture_example.py)
            result = await Runner.run(starting_agent=agent, input=query)
            print(f"Response: {result.final_output}")
            agentops.end_session(session)
        except Exception as e:
            print(f"Error: {e}")
            agentops.end_session(session, error=str(e))

async def test_with_model_override():
    """Test with explicit model setting"""
    print("\n" + "="*60)
    print("Testing with Explicit Model")
    print("="*60)

    # Try setting model explicitly
    model_name = "ollama/qwen3:4b-instruct"

    # Set LiteLLM model
    litellm.model = model_name

    # Create agent and set model attribute
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant. Use the tools to answer questions.",
        tools=[get_time, calculate]
    )

    # Try setting model on agent (might not work but worth trying)
    agent.model = model_name

    query = "What is 100 divided by 4?"
    print(f"\nQuery: {query}")
    print("-" * 40)

    session = agentops.start_session(tags={
        "model": model_name,
        "test": "explicit_model"
    })

    try:
        result = await Runner.run(starting_agent=agent, input=query)
        print(f"Response: {result.final_output}")
        agentops.end_session(session)
    except Exception as e:
        print(f"Error: {e}")
        agentops.end_session(session, error=str(e))

async def main():
    """Run tests"""
    print("\n" + "="*60)
    print("OpenAI Agents SDK + LiteLLM + Ollama Test")
    print("Following architecture_example.py pattern")
    print("="*60)

    # Test basic usage
    await test_basic()

    # Test with explicit model
    await test_with_model_override()

    print("\n" + "="*60)
    print("Test completed")
    print("="*60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        agentops.end_all_sessions()
        print("\n✅ All sessions ended")