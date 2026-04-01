from typing import TypedDict, Dict, Any
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
import json, re
# -------------------- Helpers --------------------

def parse_json_maybe(s: str) -> Dict:
    """Extract and parse JSON safely from LLM output."""
    s = (s or "").strip()
    try:
        m = re.search(r"\{.*\}", s, flags=re.S)
        if m:
            s = m.group(0).strip()
        return json.loads(s)
    except Exception as e:
        print("\n Failed to parse JSON from model output:")
        print(s)
        print("\nError:", e)
        return {}

def ensure_message(d: Dict) -> Dict:
    """Make sure 'message' is non-empty, fallback to summary/thought."""
    d = dict(d or {})
    msg = d.get("message", "").strip()
    if not msg:
        fallback = d.get("thought") or d.get("summary") or "Output ready."
        d["message"] = fallback
    return d


# -------------------- Prompts --------------------

PLANNER_SYS = """You are the Planner.
Produce exactly THREE topical tags and ONE short summary (<=25 words).
Respond STRICTLY as JSON with EXACT keys and order:
{"thought":"...", "message":"<non-empty>", "data":{"tags":["...","...","..."]}, "summary":"...", "issues":[]}
"""

REVIEWER_SYS = """
You are the Reviewer.

You must return ONLY valid JSON with these EXACT keys:
{
  "thought": "...",
  "message": "...",
  "data": {
    "tags": ["...", "...", "..."]
  },
  "summary": "...",
  "issues": [""]
}

Rules:
- Do NOT add extra text before/after the JSON.
- Do NOT add fields like 'title', 'end', etc.
- Use double quotes for all keys and values.
- The summary must be a single sentence (≤25 words).
"""




class AgentState(TypedDict):
    title: str
    content: str
    email: str
    strict: bool
    task: str
    llm: Any
    planner_proposal: Dict[str, Any]
    reviewer_feedback: Dict[str, Any]
    turn_count: int

def planner_node(state: AgentState) -> Dict[str, Any]:
    print("---NODE: Planner ---")
    llm = state["llm"]

    user_prompt = f"TITLE:\n{state['title']}\n\nCONTENT:\n{state['content']}"
    response = llm.invoke([SystemMessage(PLANNER_SYS), HumanMessage(user_prompt)])
    proposal = parse_json_maybe(response.content)
    proposal = ensure_message(proposal)

    return {"planner_proposal": proposal, "reviewer_feedback": {} }


def reviewer_node(state: AgentState) -> Dict[str, Any]:
    print("---NODE: Reviewer ---")
    llm = state["llm"]

    planner_out = state.get("planner_proposal", {})
    user_prompt = json.dumps({
        "title": state["title"],
        "content": state["content"],
        "planner": planner_out
    }, ensure_ascii=False)

    response = llm.invoke([SystemMessage(REVIEWER_SYS), HumanMessage(user_prompt)])
    feedback = parse_json_maybe(response.content)
    feedback = ensure_message(feedback)

    return {"reviewer_feedback": feedback}


def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """Update turn counter each round."""
    return {"turn_count": state["turn_count"] + 1}


def router_logic(state: AgentState) -> str:
    """Decide next node based on state."""
    if state["turn_count"] > 5: 
        return END

    if not state.get("planner_proposal"):
        return "planner"

    if not state.get("reviewer_feedback"):
        return "reviewer"

    if state["reviewer_feedback"].get("issues"):
        return "planner"


    return END


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("supervisor", supervisor_node)

    workflow.add_conditional_edges("supervisor", router_logic, {
        "planner": "planner",
        "reviewer": "reviewer",
        END: END,
    })

    workflow.add_edge("planner", "supervisor")
    workflow.add_edge("reviewer", "supervisor")

    workflow.set_entry_point("supervisor")
    return workflow.compile()


# -------------------- Run --------------------

if __name__ == "__main__":
    graph = build_graph()

    initial_state: AgentState = {
        "title": "How Reading Before Bed Improves Sleep",
        "content": """Reading before bed helps the brain relax and improves sleep
    quality by reducing stress and calming mental activity. Unlike screens,
    books do not emit blue light, making them a healthier option for winding
    down.

    Incorporating reading into a nightly routine signals the body that it's time to sleep,
    helping people fall asleep faster and wake up more refreshed.

    Research shows that even six minutes of reading can lower stress levels by more than 60%,
    making it one of the most effective bedtime habits.""",
        "email": "mounashree.prasanna@sjsu.edu",
        "strict": True,
        "task": "summarize",
        "llm": ChatOllama(model="phi3:mini", temperature=0.2),
        "planner_proposal": {},
        "reviewer_feedback": {},
        "turn_count": 0,
    }

    print("=== Running Graph ===")
    for event in graph.stream(initial_state):
        print("Event:", event)
    print("=== Done ===")