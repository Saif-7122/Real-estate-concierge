import os
from backend.agent.nodes import guardrail_node

state = {
    "user_query": "What is the price?",
    "route": "structured",
    "structured_results": [],
    "brochure_chunks": [],
    "draft_response": "The price of the apartment is 2.5 crore, and possession is by 2028."
}

print(f'--- DRAFT RESPONSE ---\n{state["draft_response"]}\n----------------------')

res_guard = guardrail_node(state)

print(f'--- FINAL RESPONSE ---\n{res_guard.get("final_response")}\n----------------------')
