---
name: langgraph-human-in-the-loop
description: "INVOKE THIS SKILL when implementing human-in-the-loop patterns, pausing for approval, or handling errors in LangGraph. Covers interrupt(), Command(resume=...), approval/validation workflows, and the 4-tier error handling strategy."
---

<overview>
LangGraph's human-in-the-loop patterns let you pause graph execution, surface data to users, and resume with their input:

- **`interrupt(value)`** — pauses execution, surfaces a value to the caller
- **`Command(resume=value)`** — resumes execution, providing the value back to `interrupt()`
- **Checkpointer** — required to save state while paused
- **Thread ID** — required to identify which paused execution to resume
</overview>

---

## Requirements

Three things are required for interrupts to work:

1. **Checkpointer** — compile with `checkpointer=InMemorySaver()` (dev) or `PostgresSaver` (prod)
2. **Thread ID** — pass `{"configurable": {"thread_id": "..."}}` to every `invoke`/`stream` call
3. **JSON-serializable payload** — the value passed to `interrupt()` must be JSON-serializable

---

## Basic Interrupt + Resume

`interrupt(value)` pauses the graph. The value surfaces in the result under `__interrupt__`. `Command(resume=value)` resumes — the resume value becomes the return value of `interrupt()`.

**Critical**: when the graph resumes, the node restarts from the **beginning** — all code before `interrupt()` re-runs.

<ex-basic-interrupt-resume>
<python>
Pause execution for human review and resume with Command.
```python
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

class State(TypedDict):
    approved: bool

def approval_node(state: State):
    # Pause and ask for approval
    approved = interrupt("Do you approve this action?")
    # When resumed, Command(resume=...) returns that value here
    return {"approved": approved}

checkpointer = InMemorySaver()
graph = (
    StateGraph(State)
    .add_node("approval", approval_node)
    .add_edge(START, "approval")
    .add_edge("approval", END)
    .compile(checkpointer=checkpointer)
)

config = {"configurable": {"thread_id": "thread-1"}}

# Initial run — hits interrupt and pauses
result = graph.invoke({"approved": False}, config)
print(result["__interrupt__"])
# [Interrupt(value='Do you approve this action?')]

# Resume with the human's response
result = graph.invoke(Command(resume=True), config)
print(result["approved"])  # True
```
</python>
</ex-basic-interrupt-resume>

---

## Approval Workflow

A common pattern: interrupt to show a draft, then route based on the human's decision.

<ex-approval-workflow>
<python>
Interrupt for human review, then route to send or end based on the decision.
```python
from langgraph.types import interrupt, Command
from langgraph.graph import StateGraph, START, END
from typing import Literal
from typing_extensions import TypedDict

class EmailAgentState(TypedDict):
    email_content: str
    draft_response: str
    classification: dict

def human_review(state: EmailAgentState) -> Command[Literal["send_reply", "__end__"]]:
    """Pause for human review using interrupt and route based on decision."""
    classification = state.get("classification", {})

    # interrupt() must come first — any code before it will re-run on resume
    human_decision = interrupt({
        "email_id": state.get("email_content", ""),
        "draft_response": state.get("draft_response", ""),
        "urgency": classification.get("urgency"),
        "action": "Please review and approve/edit this response"
    })

    # Process the human's decision
    if human_decision.get("approved"):
        return Command(
            update={"draft_response": human_decision.get("edited_response", state.get("draft_response", ""))},
            goto="send_reply"
        )
    else:
        # Rejection — human will handle directly
        return Command(update={}, goto=END)
```
</python>
</ex-approval-workflow>

---

## Validation Loop

Use `interrupt()` in a loop to validate human input and re-prompt if invalid.

<ex-validation-loop>
<python>
Validate human input in a loop, re-prompting until valid.
```python
from langgraph.types import interrupt

def get_age_node(state):
    prompt = "What is your age?"

    while True:
        answer = interrupt(prompt)

        # Validate the input
        if isinstance(answer, int) and answer > 0:
            break
        else:
            # Invalid input — ask again with a more specific prompt
            prompt = f"'{answer}' is not a valid age. Please enter a positive number."

    return {"age": answer}
```
</python>
</ex-validation-loop>

---

## Side Effects Before Interrupt Must Be Idempotent

When the graph resumes, the node restarts from the **beginning** — ALL code before `interrupt()` re-runs. In subgraphs, BOTH the parent node and the subgraph node re-execute.

<idempotency-rules>

**Do:**
- Use **upsert** (not insert) operations before `interrupt()`
- Use **check-before-create** patterns
- Place side effects **after** `interrupt()` when possible
- Separate side effects into their own nodes

**Don't:**
- Create new records before `interrupt()` — duplicates on each resume
- Append to lists before `interrupt()` — duplicate entries on each resume

</idempotency-rules>

<ex-idempotent-patterns>
<python>
Idempotent operations before interrupt vs non-idempotent (wrong).
```python
# GOOD: Upsert is idempotent — safe before interrupt
def node_a(state: State):
    db.upsert_user(user_id=state["user_id"], status="pending_approval")
    approved = interrupt("Approve this change?")
    return {"approved": approved}

# GOOD: Side effect AFTER interrupt — only runs once
def node_a(state: State):
    approved = interrupt("Approve this change?")
    if approved:
        db.create_audit_log(user_id=state["user_id"], action="approved")
    return {"approved": approved}

# BAD: Insert creates duplicates on each resume!
def node_a(state: State):
    audit_id = db.create_audit_log({  # Runs again on resume!
        "user_id": state["user_id"],
        "action": "pending_approval",
    })
    approved = interrupt("Approve this change?")
    return {"approved": approved}
```
</python>
</ex-idempotent-patterns>
