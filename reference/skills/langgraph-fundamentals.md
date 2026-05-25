---
name: langgraph-fundamentals
description: "INVOKE THIS SKILL when writing ANY LangGraph code. Covers StateGraph, state schemas, nodes, edges, Command, Send, invoke, streaming, and error handling."
---

<overview>
LangGraph models agent workflows as **directed graphs**:

- **StateGraph**: Main class for building stateful graphs
- **Nodes**: Functions that perform work and update state
- **Edges**: Define execution order (static or conditional)
- **START/END**: Special nodes marking entry and exit points
- **State with Reducers**: Control how state updates are merged

Graphs must be `compile()`d before execution.
</overview>

<design-methodology>

### Designing a LangGraph application

Follow these 5 steps when building a new graph:

1. **Map out discrete steps** — sketch a flowchart of your workflow. Each step becomes a node.
2. **Identify what each step does** — categorize nodes: LLM step, data step, action step, or user input step. For each, determine static context (prompt), dynamic context (from state), retry strategy, and desired outcome.
3. **Design your state** — state is shared memory for all nodes. Store raw data, format prompts on-demand inside nodes.
4. **Build your nodes** — implement each step as a function that takes state and returns partial updates.
5. **Wire it together** — connect nodes with edges, add conditional routing, compile with a checkpointer if needed.

</design-methodology>

<when-to-use-langgraph>

| Use LangGraph When | Use Alternatives When |
|-------------------|----------------------|
| Need fine-grained control over agent orchestration | Quick prototyping → LangChain agents |
| Building complex workflows with branching/loops | Simple stateless workflows → LangChain direct |
| Require human-in-the-loop, persistence | Batteries-included features → Deep Agents |

</when-to-use-langgraph>

---

## State Management

<state-update-strategies>

| Need | Solution | Example |
|------|----------|---------|
| Overwrite value | No reducer (default) | Simple fields like counters |
| Append to list | Reducer (operator.add / concat) | Message history, logs |
| Custom logic | Custom reducer function | Complex merging |

</state-update-strategies>

<ex-state-with-reducer>
<python>
Define state schema with reducers for accumulating lists and summing integers.
```python
from typing_extensions import TypedDict, Annotated
import operator

class State(TypedDict):
    name: str  # Default: overwrites on update
    messages: Annotated[list, operator.add]  # Appends to list
    total: Annotated[int, operator.add]  # Sums integers
```
</python>
</ex-state-with-reducer>

<fix-forgot-reducer-for-list>
<python>
Without a reducer, returning a list overwrites previous values.
```python
# WRONG: List will be OVERWRITTEN
class State(TypedDict):
    messages: list  # No reducer!

# Node 1 returns: {"messages": ["A"]}
# Node 2 returns: {"messages": ["B"]}
# Final: {"messages": ["B"]}  # "A" is LOST!

# CORRECT: Use Annotated with operator.add
from typing import Annotated
import operator

class State(TypedDict):
    messages: Annotated[list, operator.add]
# Final: {"messages": ["A", "B"]}
```
</python>
</fix-forgot-reducer-for-list>

<fix-state-must-return-dict>
<python>
Nodes must return partial updates, not mutate and return full state.
```python
# WRONG: Returning entire state object
def my_node(state: State) -> State:
    state["field"] = "updated"
    return state  # Don't mutate and return!

# CORRECT: Return dict with only the updates
def my_node(state: State) -> dict:
    return {"field": "updated"}
```
</python>
</fix-state-must-return-dict>

---

## Nodes

<node-function-signatures>

Node functions accept these arguments:

<python>

| Signature | When to Use |
|-----------|-------------|
| `def node(state: State)` | Simple nodes that only need state |
| `def node(state: State, config: RunnableConfig)` | Need thread_id, tags, or configurable values |
| `def node(state: State, runtime: Runtime[Context])` | Need runtime context, store, or stream_writer |

```python
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

def plain_node(state: State):
    return {"results": "done"}

def node_with_config(state: State, config: RunnableConfig):
    thread_id = config["configurable"]["thread_id"]
    return {"results": f"Thread: {thread_id}"}

def node_with_runtime(state: State, runtime: Runtime[Context]):
    user_id = runtime.context.user_id
    return {"results": f"User: {user_id}"}
```
</python>

</node-function-signatures>

---

## Edges

<edge-type-selection>

| Need | Edge Type | When to Use |
|------|-----------|-------------|
| Always go to same node | `add_edge()` | Fixed, deterministic flow |
| Route based on state | `add_conditional_edges()` | Dynamic branching |
| Update state AND route | `Command` | Combine logic in single node |
| Fan-out to multiple nodes | `Send` | Parallel processing with dynamic inputs |

</edge-type-selection>

<ex-basic-graph>
<python>
Simple two-node graph with linear edges.
```python
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

class State(TypedDict):
    input: str
    output: str

def process_input(state: State) -> dict:
    return {"output": f"Processed: {state['input']}"}

def finalize(state: State) -> dict:
    return {"output": state["output"].upper()}

graph = (
    StateGraph(State)
    .add_node("process", process_input)
    .add_node("finalize", finalize)
    .add_edge(START, "process")
    .add_edge("process", "finalize")
    .add_edge("finalize", END)
    .compile()
)

result = graph.invoke({"input": "hello"})
print(result["output"])  # "PROCESSED: HELLO"
```
</python>
</ex-basic-graph>

<ex-conditional-edges>
<python>
Route to different nodes based on state with conditional edges.
```python
from typing import Literal
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    query: str
    route: str
    result: str

def classify(state: State) -> dict:
    if "weather" in state["query"].lower():
        return {"route": "weather"}
    return {"route": "general"}

def route_query(state: State) -> Literal["weather", "general"]:
    return state["route"]

graph = (
    StateGraph(State)
    .add_node("classify", classify)
    .add_node("weather", lambda s: {"result": "Sunny, 72F"})
    .add_node("general", lambda s: {"result": "General response"})
    .add_edge(START, "classify")
    .add_conditional_edges("classify", route_query, ["weather", "general"])
    .add_edge("weather", END)
    .add_edge("general", END)
    .compile()
)
```
</python>
</ex-conditional-edges>

---

## Command

Command combines state updates and routing in a single return value. Fields:
- **`update`**: State updates to apply (like returning a dict from a node)
- **`goto`**: Node name(s) to navigate to next
- **`resume`**: Value to resume after `interrupt()` — see human-in-the-loop skill

<ex-command-state-and-routing>
<python>
Command lets you update state AND choose next node in one return.
```python
from langgraph.types import Command
from typing import Literal

class State(TypedDict):
    count: int
    result: str

def node_a(state: State) -> Command[Literal["node_b", "node_c"]]:
    """Update state AND decide next node in one return."""
    new_count = state["count"] + 1
    if new_count > 5:
        return Command(update={"count": new_count}, goto="node_c")
    return Command(update={"count": new_count}, goto="node_b")

graph = (
    StateGraph(State)
    .add_node("node_a", node_a)
    .add_node("node_b", lambda s: {"result": "B"})
    .add_node("node_c", lambda s: {"result": "C"})
    .add_edge(START, "node_a")
    .add_edge("node_b", END)
    .add_edge("node_c", END)
    .compile()
)
```
</python>
</ex-command-state-and-routing>

---

## Error Handling

Match the error type to the right handler:

<error-handling-table>

| Error Type | Who Fixes | Strategy | Example |
|---|---|---|---|
| Transient (network, rate limits) | System | `RetryPolicy(max_attempts=3)` | `add_node(..., retry_policy=...)` |
| LLM-recoverable (tool failures) | LLM | `ToolNode(tools, handle_tool_errors=True)` | Error returned as ToolMessage |
| User-fixable (missing info) | Human | `interrupt({"message": ...})` | Collect missing data (see HITL skill) |
| Unexpected | Developer | Let bubble up | `raise` |

</error-handling-table>

<ex-retry-policy>
<python>
Use RetryPolicy for transient errors (network issues, rate limits).
```python
from langgraph.types import RetryPolicy

workflow.add_node(
    "search_documentation",
    search_documentation,
    retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0)
)
```
</python>
</ex-retry-policy>
