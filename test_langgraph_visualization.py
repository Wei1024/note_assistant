#!/usr/bin/env python3
"""
LangGraph Visualization Demo
Demonstrates all visualization methods for LangGraph agents
"""

import asyncio
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from typing import Dict

# ============================================================================
# TOOLS - Same as comparison test
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

TOOLS = [calculate, get_weather]

# ============================================================================
# VISUALIZATION DEMO
# ============================================================================

def visualize_langgraph_agent():
    """Create and visualize a LangGraph agent using all available methods"""

    print("\n" + "="*80)
    print("LANGGRAPH VISUALIZATION DEMO")
    print("="*80)

    # Create the agent
    print("\n1. Creating LangGraph ReAct agent...")
    llm = ChatOllama(
        model="qwen3:4b-instruct",
        temperature=0.1,
    )
    agent = create_react_agent(llm, TOOLS)
    print("✅ Agent created")

    # Method 1: ASCII Visualization
    print("\n" + "="*80)
    print("METHOD 1: ASCII VISUALIZATION")
    print("="*80)
    try:
        ascii_graph = agent.get_graph().draw_ascii()
        print(ascii_graph)
    except Exception as e:
        print(f"❌ ASCII visualization not available: {e}")

    # Method 2: Mermaid Source Code
    print("\n" + "="*80)
    print("METHOD 2: MERMAID SOURCE CODE")
    print("="*80)
    print("You can copy this code and paste it into https://mermaid.live to visualize")
    print("-"*80)
    try:
        mermaid_code = agent.get_graph().draw_mermaid()
        print(mermaid_code)
    except Exception as e:
        print(f"❌ Mermaid code generation failed: {e}")

    # Method 3: PNG Visualization
    print("\n" + "="*80)
    print("METHOD 3: PNG VISUALIZATION (saved to file)")
    print("="*80)
    try:
        png_data = agent.get_graph().draw_mermaid_png()

        # Save to file
        output_file = "langgraph_agent_visualization.png"
        with open(output_file, "wb") as f:
            f.write(png_data)
        print(f"✅ Graph saved to: {output_file}")
        print("   Open this file to see the visual diagram of your agent!")
    except Exception as e:
        print(f"❌ PNG visualization failed: {e}")
        print("   Try installing dependencies: pip install grandalf")

    # Method 4: Show graph structure info
    print("\n" + "="*80)
    print("METHOD 4: GRAPH STRUCTURE INFO")
    print("="*80)
    graph = agent.get_graph()
    print(f"Number of nodes: {len(graph.nodes)}")
    print(f"Nodes: {list(graph.nodes.keys())}")
    print(f"Number of edges: {len(graph.edges)}")
    print("\nEdges (transitions):")
    for edge in graph.edges:
        print(f"  {edge.source} → {edge.target}")

# ============================================================================
# INTERACTIVE DEMO WITH ACTUAL EXECUTION
# ============================================================================

async def run_and_visualize():
    """Run the agent and show execution flow"""

    print("\n" + "="*80)
    print("INTERACTIVE DEMO: RUNNING AGENT WITH QUERY")
    print("="*80)

    from langchain_core.messages import HumanMessage

    llm = ChatOllama(
        model="qwen3:4b-instruct",
        temperature=0.1,
    )
    agent = create_react_agent(llm, TOOLS)

    query = "What's 25 * 4 and what's the weather in London?"
    print(f"\nQuery: {query}")
    print("\nExecuting agent...\n")

    result = await agent.ainvoke({
        "messages": [HumanMessage(content=query)]
    })

    # Show execution trace
    print("-"*80)
    print("EXECUTION TRACE:")
    print("-"*80)
    messages = result.get("messages", [])

    for i, msg in enumerate(messages):
        msg_type = msg.type if hasattr(msg, 'type') else type(msg).__name__
        print(f"\n[{i+1}] {msg_type.upper()}")

        if hasattr(msg, 'content'):
            content = str(msg.content)[:200]
            print(f"    {content}...")

        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"    🔧 Tool: {tc['name']}")
                print(f"       Args: {tc['args']}")

    print("\n" + "-"*80)
    print("FINAL ANSWER:")
    print("-"*80)
    final_msg = messages[-1]
    print(final_msg.content if hasattr(final_msg, 'content') else str(final_msg))

# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run visualization demos"""

    print("\n🎨 LangGraph Visualization Toolkit Demo")
    print("This script demonstrates all ways to visualize LangGraph agents\n")

    # Part 1: Static visualization
    visualize_langgraph_agent()

    # Part 2: Interactive execution
    print("\n" + "="*80)
    print("Would you like to see the agent in action? (y/n): ", end="")
    # For automated demo, just run it
    print("y")
    await run_and_visualize()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("""
LangGraph provides 3 main visualization methods:

1. ASCII (terminal-friendly):
   agent.get_graph().draw_ascii()

2. Mermaid Code (paste into mermaid.live):
   agent.get_graph().draw_mermaid()

3. PNG Image (requires grandalf):
   agent.get_graph().draw_mermaid_png()

Visualization helps you:
✅ Understand agent flow: START → agent → tools → agent → END
✅ Debug complex multi-agent systems
✅ Document your architecture
✅ Identify bottlenecks in agent reasoning

For production: Use LangGraph Studio for interactive debugging!
    """)

if __name__ == "__main__":
    asyncio.run(main())
