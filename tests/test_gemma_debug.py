#!/usr/bin/env python3
"""
Debug gemma3:4b tool calling to see what it's actually sending
"""

import asyncio
import json
import litellm

# Simple tool definition
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

async def test_gemma_raw():
    """Test gemma3 raw response"""
    print("Testing gemma3:4b raw tool calling response...")

    messages = [
        {"role": "user", "content": "Calculate 50 + 50"}
    ]

    response = await litellm.acompletion(
        model="ollama/gemma3:4b",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    message = response.choices[0].message

    print("\nRaw response object:")
    print(f"Content: {message.content}")
    print(f"Tool calls: {message.tool_calls}")

    if message.tool_calls:
        for tc in message.tool_calls:
            print(f"\nTool call details:")
            print(f"  ID: {tc.id}")
            print(f"  Type: {tc.type}")
            print(f"  Function name: {tc.function.name}")
            print(f"  Function arguments: {tc.function.arguments}")

if __name__ == "__main__":
    asyncio.run(test_gemma_raw())