from dotenv import load_dotenv
load_dotenv()

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List, Literal
from app.agent.state import PRReviewState, NodeFindingsList

llm = ChatAnthropic(model="claude-haiku-5-5")
structured_llm = llm.with_structured_output(NodeFindingsList)

# --- 1. THE MANAGER NODE ---
class ManagerDecision(BaseModel):
    reasoning: str = Field(description="Why you selected these agents")
    selected_agents: List[Literal["security_agent", "performance_agent", "logic_test_agent"]]

def agent_manager_node(state: PRReviewState) -> dict:
    """Reads the PR and decides WHICH agents are needed."""
    manager_prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are the Lead Routing Manager. Read the PR diff and route to specialists:\n"
            "- security_agent: if diff contains SQL, APIs, passwords, or authentication.\n"
            "- performance_agent: if diff contains loops, database queries, or heavy logic.\n"
            "- logic_test_agent: if diff adds complex new functions or needs unit tests.\n"
            "If it's just a text, CSS, or trivial change, return an empty list."
        )),
        ("human", "PR Title: {title}\nDiff:\n{diff}")
    ])
    
    manager_llm = llm.with_structured_output(ManagerDecision)
    decision = (manager_prompt | manager_llm).invoke({
        "title": state["pr_title"], 
        "diff": state["raw_diff"]
    })
    
    # Save the chosen agents into the queue
    return {"remaining_agents": decision.selected_agents}


# --- 2. REUSABLE SPECIALIST LOGIC ---
def _run_specialist(diff: str, role_instructions: str, agent_name: str, current_queue: List[str]) -> dict:
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a Principal Software Engineer. {role_instructions}\nReturn empty list if no issues."),
        ("human", "Diff:\n```diff\n{diff}\n```")
    ])
    
    result: NodeFindingsList = (prompt | structured_llm).invoke({
        "role_instructions": role_instructions,
        "diff": diff[:30000]
    })
    
    # Remove THIS agent from the queue so it doesn't run again
    new_queue = [a for a in current_queue if a != agent_name]
    return {"findings": result.findings, "remaining_agents": new_queue}


# --- 3. SPECIALIST NODES ---
def security_agent_node(state: PRReviewState) -> dict:
    instructions = "Focus ONLY on security: SQL injection, hardcoded secrets, auth."
    return _run_specialist(state["raw_diff"], instructions, "security_agent", state.get("remaining_agents", []))

def performance_agent_node(state: PRReviewState) -> dict:
    instructions = "Focus ONLY on performance: O(n^2) loops, N+1 queries."
    return _run_specialist(state["raw_diff"], instructions, "performance_agent", state.get("remaining_agents", []))

def logic_test_agent_node(state: PRReviewState) -> dict:
    instructions = "Focus ONLY on logic edge cases and suggest pytest unit tests."
    return _run_specialist(state["raw_diff"], instructions, "logic_test_agent", state.get("remaining_agents", []))


# --- 4. SYNTHESIZER ---
def synthesizer_node(state: PRReviewState) -> dict:
    findings = state.get("findings", [])
    if not findings:
        return {
            "final_markdown_review": "## Automated AI Code Review\n**LGTM!** The manager bypassed or specialists found zero issues."
        }

    findings_text = "\n".join([f"- [{f.severity}] {f.issue} | Fix: {f.suggested_fix}" for f in findings])
    synth_prompt = ChatPromptTemplate.from_messages([
        ("system", "Summarize findings into a clean GitHub PR review in Markdown. Do not include thinking tags."),
        ("human", "Findings:\n{findings_text}")
    ])
    
    response = (synth_prompt | llm).invoke({"findings_text": findings_text})

    # --- Extract clean string from response ---
    content = response.content
    if isinstance(content, list):
        # Join text blocks, ignoring thinking or metadata blocks
        content = "\n".join([
            block["text"] for block in content 
            if isinstance(block, dict) and block.get("type") == "text"
        ])

    return {"final_markdown_review": content}