# LangGraph Persistence Explained

## What is Persistence?

**Persistence** in LangGraph is the ability to save and restore the state of your agent execution. It enables:

- 💬 **Multi-turn conversations** (chatbots that remember context)
- 🔄 **Resume after errors** (fault tolerance)
- ⏮️ **Time travel** (replay/fork previous states)
- 👤 **Human-in-the-loop** (pause for approval, then continue)
- 🧠 **Long-term memory** (remember across sessions)

---

## Core Concepts

### 1. **Checkpoints**
A checkpoint is a snapshot of your graph's state at a specific point in execution.

Think of it like a save point in a video game:
- Saved after each "super-step" (node execution)
- Contains full state + metadata
- Can be loaded later to resume

### 2. **Threads**
A thread is a unique conversation/execution session identified by a `thread_id`.

```python
# Thread 1: User A's conversation
config_a = {"configurable": {"thread_id": "user_a_conv_1"}}

# Thread 2: User B's conversation
config_b = {"configurable": {"thread_id": "user_b_conv_1"}}

# Same graph, different memory!
graph.invoke(input_a, config_a)  # User A's context
graph.invoke(input_b, config_b)  # User B's context
```

### 3. **Checkpointers (Storage Backends)**
Checkpointers determine WHERE checkpoints are saved.

| Checkpointer | Storage | Use Case | Persists After Restart? |
|--------------|---------|----------|------------------------|
| `MemorySaver` | RAM | Development/testing | ❌ No |
| `SqliteSaver` | SQLite file | Local/single-server | ✅ Yes |
| `PostgresSaver` | Postgres DB | Production/distributed | ✅ Yes |

---

## How Persistence Works

### Without Persistence (Stateless)
```python
from langgraph.graph import StateGraph, START, END

graph = builder.compile()  # No checkpointer!

# Each call is independent
graph.invoke({"messages": ["Hello"]})
graph.invoke({"messages": ["What's my name?"]})  # Doesn't remember "Hello"
```

### With Persistence (Stateful)
```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "conversation_1"}}

# Call 1
graph.invoke({"messages": ["My name is Alice"]}, config)

# Call 2 - Remembers Call 1!
graph.invoke({"messages": ["What's my name?"]}, config)
# Response: "Your name is Alice"
```

**What happened?**
1. After Call 1, state saved to checkpoint with `thread_id="conversation_1"`
2. Call 2 loads checkpoint, sees previous messages
3. Agent has full conversation history

---

## Practical Examples

### Example 1: MemorySaver (In-Memory)

**Use case**: Quick testing, development, single process

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Define state
class State(TypedDict):
    messages: list[str]
    count: int

# Define node
def chat_node(state: State) -> dict:
    return {
        "messages": state["messages"] + [f"Processed message #{state['count']}"],
        "count": state["count"] + 1
    }

# Build graph with checkpointer
builder = StateGraph(State)
builder.add_node("chat", chat_node)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

# Create a thread
config = {"configurable": {"thread_id": "user_123"}}

# Turn 1
result1 = graph.invoke(
    {"messages": ["Hello"], "count": 0},
    config
)
print(result1)  # count = 1

# Turn 2 - Continues from previous state!
result2 = graph.invoke(
    {"messages": ["Hello"], "count": 0},  # Initial input ignored, loads from checkpoint
    config
)
print(result2)  # count = 2 (remembers previous count!)
```

**Key insight**: The second call ignores your initial state and loads from the checkpoint!

---

### Example 2: SqliteSaver (Persistent Storage)

**Use case**: Local development, single server, data survives restarts

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# Install first: pip install langgraph-checkpoint-sqlite

# Create SQLite checkpointer
with SqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": "conversation_abc"}}

    # Turn 1
    graph.invoke({"messages": ["Hello"]}, config)

    # Turn 2
    graph.invoke({"messages": ["How are you?"]}, config)

# Restart your app, state is still there!
with SqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "conversation_abc"}}

    # Continues previous conversation
    graph.invoke({"messages": ["What did we talk about?"]}, config)
```

---

### Example 3: AsyncSqliteSaver (For FastAPI)

**Use case**: Async web servers (FastAPI, etc.)

```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# In your FastAPI app
async def startup():
    checkpointer = AsyncSqliteSaver.from_conn_string("checkpoints.db")
    app.state.graph = builder.compile(checkpointer=checkpointer)

@app.post("/chat")
async def chat(message: str, user_id: str):
    config = {"configurable": {"thread_id": f"user_{user_id}"}}

    result = await app.state.graph.ainvoke(
        {"messages": [message]},
        config
    )

    return result
```

---

## Real-World Use Cases

### Use Case 1: Chatbot with Memory

```python
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict

class ChatState(TypedDict):
    messages: Annotated[list, add_messages]  # Special reducer for messages

def chatbot(state: ChatState):
    # LLM sees full conversation history
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "user_alice"}}

# Conversation 1
graph.invoke(
    {"messages": [HumanMessage(content="My favorite color is blue")]},
    config
)

# Later that day...
result = graph.invoke(
    {"messages": [HumanMessage(content="What's my favorite color?")]},
    config
)
# AI: "Your favorite color is blue!"
```

---

### Use Case 2: QuickNote AI - Classification History

**Problem**: You want to track classification decisions for debugging.

**Without persistence**:
```python
# Each classification is independent, no history
classify("Fix AWS issue")  # Standalone
classify("Meeting notes")  # No context from previous
```

**With persistence**:
```python
from langgraph.checkpoint.sqlite import SqliteSaver

class NoteState(TypedDict):
    raw_text: str
    classification_history: Annotated[list, add]  # Keep history

checkpointer = SqliteSaver.from_conn_string("~/.quicknote/classifications.db")
graph = builder.compile(checkpointer=checkpointer)

# Each user gets their own thread
config = {"configurable": {"thread_id": "user_123"}}

# Classification 1
graph.invoke({"raw_text": "Fix AWS issue"}, config)

# Classification 2 - Can see user's classification patterns!
graph.invoke({"raw_text": "Another AWS thing"}, config)
# Agent: "I notice you often classify AWS notes as 'projects'"
```

---

### Use Case 3: Human-in-the-Loop Approval

```python
from langgraph.graph import StateGraph, START, END

class ApprovalState(TypedDict):
    note: str
    suggested_folder: str
    approved: bool

def classify(state):
    return {"suggested_folder": "projects"}

def wait_for_approval(state):
    # Execution pauses here!
    # Returns special interrupt signal
    return {"approved": None}  # None = waiting

def save_note(state):
    if state["approved"]:
        save_to_folder(state["note"], state["suggested_folder"])
    return state

builder = StateGraph(ApprovalState)
builder.add_node("classify", classify)
builder.add_node("wait_approval", wait_for_approval)
builder.add_node("save", save_note)

builder.add_edge(START, "classify")
builder.add_edge("classify", "wait_approval")

def should_save(state):
    if state["approved"] is None:
        return END  # Pause, wait for user
    return "save"

builder.add_conditional_edges("wait_approval", should_save)

memory = MemorySaver()
graph = builder.compile(checkpointer=memory, interrupt_before=["save"])

config = {"configurable": {"thread_id": "note_123"}}

# Step 1: Run until approval needed
result = graph.invoke({"note": "Meeting notes"}, config)
# Execution pauses, returns suggested_folder

# Later: User approves
state = graph.get_state(config)
state.values["approved"] = True
graph.update_state(config, state.values)

# Step 2: Resume execution
graph.invoke(None, config)  # Continues from checkpoint
```

---

## Advanced Features

### 1. Get State at Any Time

```python
# Check current state
state = graph.get_state(config)
print(state.values)  # Current state
print(state.next)    # Next nodes to execute
```

### 2. Time Travel (Replay)

```python
# Get history of all checkpoints
history = graph.get_state_history(config)

for checkpoint in history:
    print(f"Step {checkpoint.metadata['step']}: {checkpoint.values}")

# Fork from a previous checkpoint
old_config = history[5].config  # Go back to step 5
graph.invoke(new_input, old_config)  # Continue from there
```

### 3. Update State Manually

```python
# Manually inject state
graph.update_state(
    config,
    {"messages": ["System: Resetting conversation"]},
    as_node="chat"
)
```

---

## Persistence for QuickNote AI

### Should You Use It?

**Probably NOT for core classification** (each note is independent)

**YES for these features:**

1. **User preferences learning**
   ```python
   class UserState(TypedDict):
       user_id: str
       tag_preferences: dict  # Learn user's tagging patterns
       folder_preferences: dict

   config = {"configurable": {"thread_id": f"user_{user_id}"}}
   # Over time, learns: "User always tags AWS notes with 'cloud'"
   ```

2. **Undo/history tracking**
   ```python
   # User: "Undo last classification"
   history = graph.get_state_history(config)
   previous_state = history[1]  # Get previous state
   graph.invoke(None, previous_state.config)  # Restore it
   ```

3. **Batch import with resume**
   ```python
   # Importing 1000 notes, crashes at #567
   # With persistence: resume from #567, don't restart
   config = {"configurable": {"thread_id": "import_job_123"}}
   ```

---

## Checkpointer Comparison

### MemorySaver
```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)
```

**Pros**:
- ✅ Zero setup
- ✅ Fast
- ✅ No dependencies

**Cons**:
- ❌ Lost on restart
- ❌ Not shared across processes
- ❌ Limited by RAM

**Use for**: Testing, development, demos

---

### SqliteSaver
```python
from langgraph.checkpoint.sqlite import SqliteSaver

# pip install langgraph-checkpoint-sqlite

checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
graph = builder.compile(checkpointer=checkpointer)
```

**Pros**:
- ✅ Persists across restarts
- ✅ Single file, easy to backup
- ✅ Good for local/single-server apps
- ✅ No server setup

**Cons**:
- ❌ Not great for high concurrency
- ❌ Single-server only (file-based)

**Use for**: QuickNote AI, local tools, single-server apps

---

### PostgresSaver
```python
from langgraph.checkpoint.postgres import PostgresSaver

# pip install langgraph-checkpoint-postgres

checkpointer = PostgresSaver.from_conn_string("postgresql://...")
graph = builder.compile(checkpointer=checkpointer)
```

**Pros**:
- ✅ Production-ready
- ✅ Multi-server (distributed)
- ✅ High concurrency
- ✅ ACID guarantees

**Cons**:
- ❌ Requires Postgres setup
- ❌ More complex

**Use for**: Production, multi-server, high traffic

---

## Quick Reference

### Basic Setup
```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "unique_id"}}
result = graph.invoke(input, config)
```

### Get State
```python
state = graph.get_state(config)
print(state.values)
```

### Get History
```python
for checkpoint in graph.get_state_history(config):
    print(checkpoint.values)
```

### Update State
```python
graph.update_state(config, {"key": "value"})
```

### Clear Thread
```python
# Delete all checkpoints for a thread
# (Not built-in, but you can implement by deleting from storage)
```

---

## Summary

**Persistence = Memory for your agent**

| Without Persistence | With Persistence |
|---------------------|------------------|
| ❌ Each call independent | ✅ Remembers across calls |
| ❌ Lost on crash | ✅ Resume after crash |
| ❌ No conversation history | ✅ Full conversation context |
| ❌ Can't undo | ✅ Time travel possible |
| ✅ Simple | ❌ More complex |

**For QuickNote AI:**
- **Core classification**: Probably don't need persistence (stateless is simpler)
- **User preferences**: YES, use SqliteSaver to learn patterns
- **Undo/history**: YES, useful feature
- **Batch operations**: YES, resume on failure

**Recommendation**: Start without persistence, add it later if you need user preference learning.
