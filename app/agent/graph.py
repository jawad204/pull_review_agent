from langgraph.graph import StateGraph, START, END
from app.agent.state import PRReviewState
from app.agent.nodes import (
    agent_manager_node,
    security_agent_node,
    performance_agent_node,
    logic_test_agent_node,
    synthesizer_node,
)

def route_next_agent(state: PRReviewState) -> str:
    """Checks the queue. Routes to the next agent, or Synthesizer if empty."""
    queue = state.get("remaining_agents", [])
    if not queue:
        return "synthesizer"
    
    # Return the exact name of the next agent in the queue
    return queue[0]

def build_pr_review_graph():
    builder = StateGraph(PRReviewState)

    builder.add_node("agent_manager", agent_manager_node)
    builder.add_node("security_agent", security_agent_node)
    builder.add_node("performance_agent", performance_agent_node)
    builder.add_node("logic_test_agent", logic_test_agent_node)
    builder.add_node("synthesizer", synthesizer_node)

    # 1. START goes directly to the Manager
    builder.add_edge(START, "agent_manager")

    # 2. After Manager makes the queue, we route to the first chosen agent
    all_possible_destinations = ["security_agent", "performance_agent", "logic_test_agent", "synthesizer"]
    
    builder.add_conditional_edges("agent_manager", route_next_agent, all_possible_destinations)

    # 3. After ANY agent finishes and pops itself from the queue, we route again!
    builder.add_conditional_edges("security_agent", route_next_agent, all_possible_destinations)
    builder.add_conditional_edges("performance_agent", route_next_agent, all_possible_destinations)
    builder.add_conditional_edges("logic_test_agent", route_next_agent, all_possible_destinations)

    # 4. Synthesizer ends the workflow
    builder.add_edge("synthesizer", END)

    return builder.compile()

pr_review_graph = build_pr_review_graph()