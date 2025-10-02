#!/usr/bin/env python3
"""
Debug test for LiteLLM integration with OpenAI Agents SDK
"""

import asyncio
from agents import Agent, Runner, function_tool
from agents.extensions.models.litellm_model import LitellmModel

@function_tool
def get_time() -> str:
    """Get the current time."""
    from datetime import datetime
    return f"The current time is {datetime.now().strftime('%H:%M:%S')}"

async def main():
    print("Testing LiteLLM integration...")

    # Create LiteLLM model for Ollama
    print("Creating LiteLLM model for ollama/qwen3:4b-instruct...")
    litellm_model = LitellmModel(
        model="ollama/qwen3:4b-instruct",
        api_key="dummy"  # Ollama doesn't use API keys
    )

    # Create simple agent
    print("Creating agent...")
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant. Use the get_time tool when asked about time.",
        model=litellm_model,
        tools=[get_time]
    )

    # Test query
    query = "What time is it?"
    print(f"Running query: {query}")

    try:
        result = await Runner.run(
            starting_agent=agent,
            input=query
        )
        print(f"Success! Response: {result.final_output}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())