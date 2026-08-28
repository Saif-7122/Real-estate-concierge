from langgraph.graph import StateGraph, START, END
from backend.agent.state import ConciergeState
from backend.agent.nodes import (
    router_node,
    structured_retrieval_node,
    brochure_retrieval_node,
    generation_node,
    guardrail_node
)

workflow = StateGraph(ConciergeState)

# Add all nodes to the graph
workflow.add_node("router", router_node)
workflow.add_node("structured_retrieval", structured_retrieval_node)
workflow.add_node("brochure_retrieval", brochure_retrieval_node)
workflow.add_node("generate", generation_node)
workflow.add_node("guardrail_check", guardrail_node)

def route_after_router(state: ConciergeState) -> str:
    """Determine the next node based on the router's classification."""
    route = state.get("route", "both")
    if route == "structured":
        return "structured_retrieval"
    elif route == "brochure":
        return "brochure_retrieval"
    else:
        # For 'both', we start with structured_retrieval
        return "structured_retrieval"

def route_after_structured(state: ConciergeState) -> str:
    """Determine where to go after structured retrieval based on the route."""
    route = state.get("route", "both")
    if route == "both":
        return "brochure_retrieval"
    return "generate"

# Wire the edges
workflow.add_edge(START, "router")
workflow.add_conditional_edges(
    "router", 
    route_after_router,
    {
        "structured_retrieval": "structured_retrieval",
        "brochure_retrieval": "brochure_retrieval"
    }
)

workflow.add_conditional_edges(
    "structured_retrieval",
    route_after_structured,
    {
        "brochure_retrieval": "brochure_retrieval",
        "generate": "generate"
    }
)

workflow.add_edge("brochure_retrieval", "generate")
workflow.add_edge("generate", "guardrail_check")
workflow.add_edge("guardrail_check", END)

# Compile the final agent application
concierge_app = workflow.compile()
