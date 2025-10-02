# OpenAI Agents SDK - Implementation Guide

## Overview

The OpenAI Agents SDK provides a production-ready framework for building intelligent agents with tool calling capabilities. This guide covers how to use it with local LLMs via Ollama for the QuickNote AI backend.

## Key Concepts

### 1. Agent Definition

Agents are configured with:
- **Name**: Unique identifier
- **Instructions**: System prompt defining behavior
- **Tools**: Functions the agent can call
- **Model**: LLM to use (can be local via Ollama)

```python
from agents import Agent, function_tool

agent = Agent(
    name="Note Organizer",
    instructions="Your role and capabilities...",
    tools=[organize_note, save_note, search_notes],
    model="qwen3:4b-instruct"
)
```

### 2. Tool Definition Pattern

Tools are Python functions decorated with `@function_tool`:

```python
from agents import function_tool
from typing import List, Dict

@function_tool
def save_note(title: str, folder: str, tags: List[str], content: str) -> Dict:
    """
    Save a note to the filesystem.

    Args:
        title: Note title
        folder: Target folder (inbox, projects, etc.)
        tags: List of tags
        content: Note content

    Returns:
        Dictionary with save result
    """
    # Implementation
    return {"id": note_id, "path": file_path}
```

**Important**: The docstring is used by the LLM to understand when and how to use the tool.

### 3. Running Agents

Use the `Runner` class for async execution:

```python
from agents import Runner
from openai import AsyncOpenAI

# Configure Ollama client
client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"  # Required but unused
)

# Run agent
result = await Runner.run(
    starting_agent=agent,
    input="User input here",
    model_client=client,
    model="qwen3:4b-instruct"
)
```

### 4. Structured Outputs

Use Pydantic models for structured responses:

```python
from pydantic import BaseModel, Field

class NoteOrganization(BaseModel):
    title: str = Field(description="Concise title")
    folder: str = Field(description="Target folder")
    tags: List[str] = Field(description="Relevant tags")

agent = Agent(
    name="Organizer",
    instructions="...",
    output_type=NoteOrganization  # Enforces structured output
)
```

## Local Model Integration (Ollama)

### Setup

1. Install Ollama:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

2. Pull model:
```bash
ollama pull qwen3:4b-instruct
```

3. Start Ollama server:
```bash
ollama serve  # Default: http://localhost:11434
```

### Configuration

```python
from openai import AsyncOpenAI

# Ollama provides OpenAI-compatible API
ollama_client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"  # Required by SDK but not used by Ollama
)

# Use with agent
result = await Runner.run(
    starting_agent=agent,
    input=query,
    model_client=ollama_client,
    model="qwen3:4b-instruct"
)
```

## Tool Calling Flow

1. **User Input** → Agent receives query
2. **Analysis** → Agent determines required tools
3. **Tool Selection** → Agent calls appropriate tool(s)
4. **Execution** → Tool function executes
5. **Processing** → Agent processes tool results
6. **Response** → Agent formulates final response

### Example Flow

```python
# User input: "Save this note about meeting with Sarah"
#
# Agent thinks: "I need to:
#   1. Analyze the content to extract metadata
#   2. Save the note with proper organization"
#
# Agent calls:
#   1. organize_note(content) → {title, folder, tags}
#   2. save_note(title, folder, tags, content) → {id, path}
#
# Agent responds: "Saved 'Meeting with Sarah' to people/2025-01-23-meeting-sarah.md"
```

## Advanced Features

### 1. Multi-Agent Handoffs

```python
inbox_agent = Agent(
    name="Inbox Handler",
    instructions="Process uncategorized notes"
)

project_agent = Agent(
    name="Project Organizer",
    instructions="Handle technical project notes"
)

router_agent = Agent(
    name="Router",
    instructions="Route notes to appropriate specialist",
    handoffs=[inbox_agent, project_agent]
)
```

### 2. Input Validation (Guardrails)

```python
def validate_note_length(input: str) -> bool:
    """Ensure note is not too long"""
    return len(input) < 10000

agent = Agent(
    name="Note Processor",
    instructions="...",
    input_guardrails=[validate_note_length]
)
```

### 3. Tool Choice Control

```python
from agents import ModelSettings

agent = Agent(
    name="Focused Agent",
    tools=[save_note, organize_note],
    model_settings=ModelSettings(
        tool_choice="organize_note"  # Force specific tool
    )
)
```

### 4. Custom Tool Behavior

```python
agent = Agent(
    name="Fast Agent",
    tools=[quick_save],
    tool_use_behavior="stop_on_first_tool"  # Don't process tool results
)
```

## Error Handling

### Fallback Strategy

```python
async def process_note_with_fallback(content: str):
    try:
        # Try agent processing
        result = await Runner.run(agent, content)
        return result
    except Exception as e:
        # Fallback to simple save
        return save_to_inbox(content)
```

### Tool Error Handling

```python
@function_tool
def resilient_save(title: str, content: str) -> Dict:
    """Save with retry logic"""
    for attempt in range(3):
        try:
            return do_save(title, content)
        except IOError:
            if attempt == 2:
                return {"error": "Failed after 3 attempts"}
            await asyncio.sleep(1)
```

## Performance Optimization

### 1. Model Selection
- Use smaller models (3B-7B) for speed
- Consider quantized versions (4-bit, 8-bit)
- Enable GPU acceleration if available

### 2. Caching
```python
from functools import lru_cache

@lru_cache(maxsize=100)
@function_tool
def cached_search(query: str) -> List[Dict]:
    """Cached search for repeated queries"""
    return perform_search(query)
```

### 3. Async Operations
```python
# Process multiple notes concurrently
results = await asyncio.gather(
    process_note(note1),
    process_note(note2),
    process_note(note3)
)
```

## Testing

### Unit Testing Tools

```python
import pytest
from agents import function_tool

@function_tool
def test_tool(input: str) -> str:
    return f"Processed: {input}"

@pytest.mark.asyncio
async def test_agent():
    agent = Agent(
        name="Test Agent",
        instructions="Test instructions",
        tools=[test_tool]
    )

    result = await Runner.run(agent, "test input")
    assert result.final_output is not None
```

### Mock LLM for Testing

```python
class MockLLMClient:
    async def chat(self, messages, tools=None):
        # Return predetermined responses
        return {"content": "Mock response"}

# Use in tests
result = await Runner.run(
    agent,
    "test",
    model_client=MockLLMClient()
)
```

## Production Considerations

### 1. Monitoring
- Track tool call frequency
- Monitor response times
- Log errors and fallbacks

### 2. Rate Limiting
- Implement request queuing
- Add cooldown periods
- Batch similar requests

### 3. Security
- Validate all tool inputs
- Sanitize file paths
- Limit tool permissions

### 4. Scalability
- Use connection pooling
- Implement request caching
- Consider multi-instance deployment

## Integration with FastAPI

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Shared agent instance
note_agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global note_agent
    note_agent = create_note_agent()
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/process")
async def process(content: str):
    result = await Runner.run(note_agent, content)
    return {"result": result.final_output}
```

## Next Steps

1. **Implement core tools** for note management
2. **Configure Ollama** with optimal model
3. **Add monitoring** and error tracking
4. **Test tool calling** with various inputs
5. **Optimize performance** based on usage patterns

## Resources

- [OpenAI Agents SDK Docs](https://openai.github.io/openai-agents-python/)
- [Ollama Documentation](https://ollama.com/docs)
- [Model Context Protocol](https://github.com/modelcontextprotocol)
- [LiteLLM for multi-model support](https://github.com/BerriAI/litellm)