import sys
import os

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backend.agent.graph import concierge_app
from backend.agent.state import ConciergeState

queries = [
    "what are the key properties",
    "how many 3 BHK flats",
    "by when is it available"
]

state = ConciergeState(buyer_profile={}, conversation_history=[])

for q in queries:
    print(f"\nUser: {q}")
    state["user_query"] = q
    # We must invoke the graph and get the resulting state
    result = concierge_app.invoke(state)
    
    # Print the AI's response
    print(f"AI: {result['final_response']}")
    
    # The new state should have the updated buyer_profile
    if "buyer_profile" in result:
        state["buyer_profile"] = result["buyer_profile"]
    
    # Also update conversation history for the next turn
    state["conversation_history"].append({"role": "user", "content": q})
    state["conversation_history"].append({"role": "assistant", "content": result['final_response']})

