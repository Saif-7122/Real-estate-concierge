import sys, os
sys.path.insert(0, os.path.abspath("."))
from backend.agent.graph import concierge_app
from backend.agent.state import ConciergeState

state = ConciergeState(buyer_profile={}, conversation_history=[])
q = "whats the price of a 3bhk in tower a"
state["user_query"] = q
result = concierge_app.invoke(state)
print(f"AI:   {result['final_response']}")
