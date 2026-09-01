import os
import sys
from dotenv import load_dotenv

load_dotenv()

from backend.agent.nodes import generation_node, guardrail_node

state = {
    "user_query": "Please reply exactly with this text: The price is 2.5 crore and possession is 2028.",
    "route": "structured",
    "structured_results": [],
    "brochure_chunks": []
}

res_gen = generation_node(state)
draft = res_gen.get('draft_response', '')
print(f'--- DRAFT RESPONSE ---\n{draft}\n----------------------')

state['draft_response'] = draft
res_guard = guardrail_node(state)

print(f'--- FINAL RESPONSE ---\n{res_guard.get("final_response")}\n----------------------')
