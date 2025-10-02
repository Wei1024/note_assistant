#!/usr/bin/env python3
"""
Debug why gemma3:4b fails with OpenAI Agents SDK
Track the full execution flow
"""

import asyncio
from agents import Agent, Runner, function_tool
from agents.extensions.models.litellm_model import LitellmModel
import json

@function_tool
def calculate(expression: str) -> str:
    """Calculate a mathematical expression."""
    try:
        result = eval(expression, {"__builtins__": {}})
        return f"The result is {result}"
    except Exception as e:
        return f"Error: {e}"

async def test_gemma_with_agent():
    """Test gemma3:4b with OpenAI Agents SDK step by step"""

    print("="*60)
    print("Testing gemma3:4b with OpenAI Agents SDK")
    print("="*60)

    # Create LiteLLM model for gemma3
    gemma_model = LitellmModel(
        model="ollama/gemma3:4b",
        api_key="dummy"
    )

    # Create agent
    agent = Agent(
        name="Gemma Calculator",
        instructions="""You are a calculator assistant.
        When asked to calculate, use the calculate tool.
        After getting the result, provide it to the user.""",
        model=gemma_model,
        tools=[calculate]
    )

    # Print tool info
    print("\nAgent tools registered:")
    for tool in agent.tools:
        print(f"  - Tool: {tool}")
        if hasattr(tool, 'name'):
            print(f"    Name attribute: {tool.name}")
        if hasattr(tool, '__dict__'):
            print(f"    Attributes: {tool.__dict__.keys()}")

    query = "Calculate 50 + 50"
    print(f"\nQuery: {query}")
    print("-"*40)

    try:
        # Run with more turns to see what happens
        result = await Runner.run(
            starting_agent=agent,
            input=query,
            max_turns=10  # More turns to see the pattern
        )
        print(f"✅ Success! Final output: {result.final_output}")
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Error type: {type(e).__name__}")

        # Try to get more details
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

async def test_direct_litellm_with_gemma():
    """Test gemma3 directly with LiteLLM to see tool behavior"""

    print("\n" + "="*60)
    print("Testing gemma3:4b directly with LiteLLM")
    print("="*60)

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
                            "description": "The math expression"
                        }
                    },
                    "required": ["expression"]
                }
            }
        }
    ]

    messages = [
        {
            "role": "system",
            "content": "You are a calculator. Use the calculate tool when asked to do math."
        },
        {
            "role": "user",
            "content": "Calculate 50 + 50"
        }
    ]

    import litellm

    for turn in range(3):
        print(f"\n--- Turn {turn + 1} ---")

        response = await litellm.acompletion(
            model="ollama/gemma3:4b",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        message = response.choices[0].message

        if message.tool_calls:
            print(f"Tool call received:")
            for tc in message.tool_calls:
                print(f"  Function: {tc.function.name}")
                print(f"  Arguments: {tc.function.arguments}")

                # Add assistant message with tool call
                messages.append({
                    "role": "assistant",
                    "tool_calls": [{
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }]
                })

                # Execute and add tool result
                args = json.loads(tc.function.arguments)
                result = eval(args["expression"], {"__builtins__": {}})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result)
                })

                print(f"  Result: {result}")
        else:
            print(f"Final response: {message.content}")
            break

async def main():
    """Run all tests"""
    await test_gemma_with_agent()
    await test_direct_litellm_with_gemma()

if __name__ == "__main__":
    asyncio.run(main())