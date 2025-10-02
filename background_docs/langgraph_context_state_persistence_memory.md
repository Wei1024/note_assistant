# LangGraph: Context vs State vs Persistence vs Memory

Quick reference guide for understanding the four key data management concepts in LangGraph.

---

## **TL;DR**

| Concept | What It Is | Lifespan | Changes? | Example |
|---------|-----------|----------|----------|---------|
| **Context** | Static config/metadata | Single run | ❌ No | User ID, API keys, system prompt |
| **State** | Working memory | Single run | ✅ Yes (every step) | Messages, intermediate results |
| **Persistence** | Saved state snapshots | Single thread | ✅ Yes (checkpointed) | Chat history, resume point |
| **Memory** | Long-term knowledge | Cross-thread | ✅ Yes (learned over time) | User preferences, patterns |

---

## **1. Context** - Static Runtime Data

**Purpose**: Provide immutable configuration when starting the agent

**Lifespan**: Single invocation (one `graph.invoke()` call)

**Use for**:
- User metadata (ID, name, timezone)
- Database connections
- API keys
- System prompts
- Configuration settings

**Example**:
```python
graph.invoke(
    input_data,
    context={
        "user_id": "alice_123",
        "timezone": "America/New_York",
        "db_connection": db,
        "api_key": "sk-..."
    }
)

# Access in nodes
def my_node(state: State, *, context: dict):
    user_id = context["user_id"]
    timezone = context["timezone"]
    # Use context to customize behavior
```

**Key characteristic**: **Never changes during execution**

---

## **2. State** - Dynamic Working Memory

**Purpose**: Track data that evolves as the graph executes

**Lifespan**: Single run (modified by each node)

**Use for**:
- Current messages
- Intermediate results
- Tool outputs
- Counters, flags
- Work-in-progress data

**Example**:
```python
from typing import TypedDict, Annotated
from operator import add

class State(TypedDict):
    messages: Annotated[list, add]  # Appends messages
    count: int                       # Updated by nodes
    result: str                      # Set by final node

def node1(state: State) -> dict:
    return {"count": state["count"] + 1}  # State changes!

def node2(state: State) -> dict:
    return {"result": f"Processed {state['count']} times"}
```

**Key characteristic**: **Changes with every node execution**

---

## **3. Persistence** - Saved State Checkpoints

**Purpose**: Save state snapshots to resume conversations later

**Lifespan**: Single thread (conversation), survives restarts

**Use for**:
- Multi-turn conversations
- Resume after errors
- Undo/time travel
- Human-in-the-loop

**Example**:
```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

# Option 1: In-memory (lost on restart)
memory = MemorySaver()

# Option 2: SQLite (persists across restarts)
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

graph = builder.compile(checkpointer=checkpointer)

# Each thread has its own history
config = {"configurable": {"thread_id": "conversation_1"}}

# Turn 1
graph.invoke({"messages": ["Hello"]}, config)

# Turn 2 - Remembers Turn 1
graph.invoke({"messages": ["What's my name?"]}, config)

# Different thread - separate history
config2 = {"configurable": {"thread_id": "conversation_2"}}
graph.invoke({"messages": ["Hi"]}, config2)  # No memory of conversation_1
```

**Key characteristic**: **Thread-scoped** (one conversation thread)

---

## **4. Memory (Store)** - Long-Term Knowledge

**Purpose**: Store facts/preferences that span ALL conversations

**Lifespan**: Cross-thread (global or user-scoped), permanent

**Use for**:
- User preferences
- Learned patterns
- Historical facts
- Domain knowledge
- User profiles

**Example**:
```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
graph = builder.compile(checkpointer=memory, store=store)

# Store user preference (available in ALL threads)
store.put(
    ("user_alice", "preferences"),  # Namespace
    "response_style",                # Key
    {"style": "concise", "tone": "direct"}  # Value
)

# Later, in ANY conversation thread
def my_node(state: State, *, store: BaseStore):
    # Retrieve user preferences
    prefs = store.search(
        ("user_alice", "preferences"),
        query="response style"
    )
    # Customize response based on learned preferences
    return {"response": format_response(prefs)}
```

**Key characteristic**: **Cross-thread** (shared across all conversations)

---

## **Visual Comparison**

### **Scope & Lifespan**

```
Context        [==================]  One run
State          [==================]  One run (changes each step)
Persistence    [==========================================]  One thread (many runs)
Memory         [==================================================...]  Forever (all threads)

               Run 1    Run 2    Run 3    Run 4
Thread 1:      [====]   [====]   [====]   ← Persistence saves across runs
Thread 2:                        [====]   [====]  ← Different thread
                  ↓        ↓        ↓        ↓
All threads share Memory  → [User prefers concise responses]
```

---

## **Real-World Analogy: Claude.ai Web App**

| Concept | Claude.ai Example |
|---------|-------------------|
| **Context** | System prompt, user name, account tier |
| **State** | Current conversation messages, web search results, file edits |
| **Persistence** | Saved chat history (conversation threads in sidebar) |
| **Memory** | Custom instructions, "Remember I prefer Python", learned preferences |

---

## **When to Use Each**

### ✅ **Use Context** when:
- Data doesn't change during execution
- Passing configuration/credentials
- User metadata known upfront

### ✅ **Use State** when:
- Data evolves as graph executes
- Tracking intermediate results
- Building up a response step-by-step

### ✅ **Use Persistence** when:
- Multi-turn conversations
- Need to resume after errors
- Want conversation history
- Human approval workflows

### ✅ **Use Memory** when:
- Learning user preferences over time
- Sharing knowledge across conversations
- Building user profiles
- Detecting patterns across sessions

---

## **QuickNote AI Application**

### **Context** (Use ✅):
```python
graph.invoke(
    {"raw_text": "Fix AWS issue"},
    context={
        "user_id": "alice",
        "notes_dir": "~/Notes",
        "editor_cmd": "code"
    }
)
```

### **State** (Use ✅):
```python
class NoteState(TypedDict):
    raw_text: str      # Input
    title: str         # Generated by LLM
    folder: str        # Generated by LLM
    tags: list[str]    # Generated by LLM
    error: str | None  # Validation errors
```

### **Persistence** (Skip for MVP ⏭️):
```python
# Each note classification is independent
# No need to resume conversations
```

### **Memory** (Add in v2 ⏭️):
```python
# Learn over time:
# "User always tags AWS notes with 'cloud'"
# "User prefers 'projects' folder for infrastructure notes"
```

---

## **Code Example: All Four Together**

```python
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore

# 1. STATE: Define working data
class State(TypedDict):
    messages: list
    result: str

# 2. PERSISTENCE: Setup checkpointer
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

# 3. MEMORY: Setup store
store = InMemoryStore()

# Build graph
builder = StateGraph(State)
builder.add_node("process", process_node)
graph = builder.compile(
    checkpointer=checkpointer,  # Persistence
    store=store                  # Memory
)

# 4. CONTEXT: Pass runtime config
result = graph.invoke(
    {"messages": ["Hello"]},           # Initial state
    context={                           # Context
        "user_id": "alice",
        "api_key": "sk-..."
    },
    config={                            # Persistence config
        "configurable": {
            "thread_id": "conv_123"
        }
    }
)
```

---

## **Common Patterns**

### **Pattern 1: Stateless API** (Context + State only)
```python
# Simple, one-shot operations
graph = builder.compile()  # No checkpointer, no store

result = graph.invoke(
    input_data,
    context={"user_id": "alice"}
)
```

### **Pattern 2: Chatbot** (Context + State + Persistence)
```python
# Multi-turn conversations
checkpointer = SqliteSaver.from_conn_string("chats.db")
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "user_123_chat"}}
graph.invoke(message, context=user_info, config=config)
```

### **Pattern 3: Personalized Agent** (All Four)
```python
# Learning assistant with memory
checkpointer = SqliteSaver.from_conn_string("chats.db")
store = InMemoryStore()
graph = builder.compile(checkpointer=checkpointer, store=store)

# Remembers across sessions, learns preferences
graph.invoke(message, context=user_info, config=thread_config)
```

---

## **Summary**

**Context** = "Who is using this?" (user metadata)
**State** = "What's happening now?" (current execution)
**Persistence** = "What did we talk about?" (conversation history)
**Memory** = "What do I know about you?" (long-term knowledge)

**Start simple**: Use Context + State
**Add later**: Persistence (for conversations), Memory (for learning)

---

## **Quick Reference: Storage Backends**

### **Persistence (Checkpointers)**:
```python
from langgraph.checkpoint.memory import MemorySaver         # In-memory
from langgraph.checkpoint.sqlite import SqliteSaver         # SQLite file
from langgraph.checkpoint.postgres import PostgresSaver     # PostgreSQL
```

### **Memory (Stores)**:
```python
from langgraph.store.memory import InMemoryStore            # In-memory
from langgraph.store.postgres import PostgresStore          # PostgreSQL
```

---

## **Further Reading**

- [LangGraph Persistence](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [LangGraph Memory](https://langchain-ai.github.io/langgraph/concepts/memory/)
- [Agent Context](https://langchain-ai.github.io/langgraph/agents/context/)
- [Low-Level Concepts](https://langchain-ai.github.io/langgraph/concepts/low_level/)
