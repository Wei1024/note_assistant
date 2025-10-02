# QuickNote AI - OpenAI Agents SDK Architecture

## Overview

This document outlines the architecture for QuickNote AI's backend using the OpenAI Agents SDK with local LLM support via Ollama. This approach provides a production-ready agent framework with tool calling capabilities while maintaining complete data privacy through local model execution.

## Core Architecture

### 1. Agent Framework Layer

The OpenAI Agents SDK provides the foundation for intelligent note organization:

```python
from agents import Agent, Runner

agent = Agent(
    name="Note Organizer",
    instructions="""You are a note organization assistant.
    Analyze notes and categorize them with appropriate titles, folders, and tags.
    Use available tools to save and search notes.""",
    mcp_servers=[note_tools_server],  # Tools provided via MCP
)
```

**Key Features:**
- Async execution model
- Built-in conversation management
- Tool orchestration
- Error handling and retries

### 2. Model Integration Layer

#### Local Model Support (Primary)

Using Ollama for local model execution:

```python
from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel

# Configure local Qwen model via Ollama
local_model = OpenAIChatCompletionsModel(
    model="qwen3:4b-instruct",
    openai_client=AsyncOpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama"  # Required but unused
    )
)
```

#### Multi-Model Flexibility (Optional)

LiteLLM integration for model switching:

```python
import litellm

# Support for 100+ models with single interface
litellm.set_verbose = False
litellm.model = "ollama/qwen3:4b-instruct"

# Can easily switch to other providers
# litellm.model = "gpt-4"  # OpenAI
# litellm.model = "claude-3"  # Anthropic
```

### 3. Tool System via Model Context Protocol (MCP)

MCP provides a standardized way to expose tools to the agent:

```python
from agents import MCPServerStdio

# Note management tools server
note_tools_server = MCPServerStdio(
    name="Note Tools Server",
    params={
        "command": "python",
        "args": ["-m", "note_tools_mcp", "--notes-dir", NOTES_DIR],
    },
)
```

#### Tool Implementation Pattern

Create a Python MCP server that exposes note operations:

```python
# note_tools_mcp.py
from mcp import Server, Tool

server = Server("note-tools")

@server.tool()
async def save_note(
    title: str,
    folder: str,
    tags: list[str],
    content: str
) -> dict:
    """Save a note with metadata to the filesystem"""
    # Implementation
    return {"id": note_id, "path": file_path}

@server.tool()
async def search_notes(query: str, limit: int = 20) -> list:
    """Search notes using FTS5"""
    # Implementation
    return search_results

@server.tool()
async def organize_note(content: str) -> dict:
    """Suggest organization for a note"""
    # Implementation
    return {
        "title": suggested_title,
        "folder": suggested_folder,
        "tags": suggested_tags
    }
```

### 4. Agent Execution Flow

```python
async def process_note(user_input: str) -> dict:
    """Process a note through the agent pipeline"""

    # 1. Create agent with note organization instructions
    agent = Agent(
        name="Note Organizer",
        instructions=NOTE_ORGANIZATION_PROMPT,
        mcp_servers=[note_tools_server],
    )

    # 2. Execute agent with user input
    result = await Runner.run(
        starting_agent=agent,
        input=user_input,
        model=local_model,  # Use local Qwen model
    )

    # 3. Return structured result
    return {
        "success": True,
        "note_id": result.metadata.get("note_id"),
        "organization": result.metadata.get("organization"),
        "output": result.final_output
    }
```

## Tool Calling Flow

1. **User Input** → Agent receives raw note text
2. **Agent Analysis** → Agent determines required actions
3. **Tool Selection** → Agent selects appropriate tools based on task
4. **Tool Execution** → MCP server executes tool functions
5. **Result Processing** → Agent processes tool results
6. **Response Generation** → Agent formulates final response

### Example Tool Call Sequence

```
User: "Met with Sarah about dashboard design, using card layout"
         ↓
Agent: Calls organize_note(content)
         ↓
Tool: Returns {title: "Dashboard Design Meeting",
               folder: "projects",
               tags: ["design", "meeting"]}
         ↓
Agent: Calls save_note(title, folder, tags, content)
         ↓
Tool: Returns {id: "2025-01-23_abc123", path: "~/Notes/projects/..."}
         ↓
Agent: "Saved to projects/dashboard-design-meeting.md"
```

## Dependencies

### Core Requirements

```txt
# requirements.txt
agents==0.2.0          # OpenAI Agents SDK
ollama==0.1.7          # Local model client
openai==1.0.0          # OpenAI client (for Ollama compatibility)
litellm==1.20.0        # Optional: Multi-model support
fastapi==0.104.0       # API server
uvicorn==0.24.0        # ASGI server
pydantic==2.5.0        # Data validation
```

### System Requirements

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull Qwen model
ollama pull qwen3:4b-instruct

# Start Ollama server
ollama serve  # Runs on http://localhost:11434
```

## Monitoring & Observability

### Agent Tracing

```python
import agentops

# Initialize tracing
agentops.init(api_key="your-key")

# Trace agent execution
session = agentops.start_session(tags={
    "model": "qwen3:4b-instruct",
    "task": "note_organization",
})

try:
    result = await Runner.run(agent, input=query)
    agentops.end_session(session, success=True)
except Exception as e:
    agentops.end_session(session, error=str(e))
    raise
```

### Metrics Collection

```python
# Track key metrics
metrics = {
    "response_time": time.elapsed,
    "tokens_used": result.token_count,
    "tools_called": len(result.tool_calls),
    "model": model_name,
}
```

## Error Handling & Fallbacks

### Model Fallback Strategy

```python
async def process_with_fallback(input: str):
    try:
        # Primary: Local Qwen model
        return await process_note(input)
    except ModelUnavailableError:
        # Fallback 1: Direct JSON extraction
        return await extract_json_metadata(input)
    except Exception as e:
        # Fallback 2: Save to inbox
        return save_to_inbox(input)
```

### Tool Error Handling

```python
@server.tool()
async def resilient_save_note(**kwargs):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await save_note(**kwargs)
        except FileSystemError as e:
            if attempt == max_retries - 1:
                # Final fallback: save to temp location
                return await save_to_temp(**kwargs)
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

## Performance Optimization

### 1. Model Optimization
- Use quantized models (4-bit, 8-bit) for faster inference
- Enable GPU acceleration if available
- Implement response caching for similar queries

### 2. Tool Execution
- Parallelize independent tool calls
- Implement connection pooling for database operations
- Use async I/O for file operations

### 3. Memory Management
- Stream large responses instead of loading in memory
- Implement context window management
- Clear conversation history after note processing

## Security Considerations

### Local Execution
- All LLM inference happens locally
- No data leaves the machine
- Complete control over model and data

### Access Control
- MCP servers run in isolated processes
- Tool permissions can be restricted
- File system access limited to Notes directory

### Data Validation
- Pydantic models for all inputs/outputs
- Sanitize file paths and names
- Validate JSON responses from LLM

## Advantages of This Architecture

1. **Privacy First** - Complete local execution, no cloud dependencies
2. **Tool Extensibility** - Easy to add new capabilities via MCP
3. **Model Flexibility** - Switch between local/cloud models seamlessly
4. **Production Ready** - Built-in error handling, tracing, and monitoring
5. **Standards Based** - Uses OpenAI API standards for compatibility
6. **Cost Effective** - No API costs for local model usage

## Future Enhancements

1. **Multi-Agent Support** - Specialized agents for different note types
2. **Memory Systems** - Long-term memory for user preferences
3. **Embedding Search** - Semantic search using local embeddings
4. **Voice Integration** - Local Whisper for voice notes
5. **Plugin System** - User-defined tools and workflows

## Conclusion

This architecture leverages the OpenAI Agents SDK to create a robust, privacy-focused note organization system. By combining local LLM execution via Ollama with the agent framework's tool calling capabilities, we achieve enterprise-grade functionality without compromising on data privacy or incurring API costs.