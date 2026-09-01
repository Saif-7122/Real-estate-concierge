import sys, os, time
sys.path.insert(0, os.path.abspath("."))
from backend.agent.graph import concierge_app
from backend.agent.state import ConciergeState

queries = [
    "hi",
    "how many units are available now",
    "who is the builder",
    "is he well known",
    "how many 3 bhk east facing are available",
    "whats the price of a 3bhk in tower a",
]

state = ConciergeState(buyer_profile={}, conversation_history=[])

for q in queries:
    print(f"\nUser: {q}")
    state["user_query"] = q
    result = concierge_app.invoke(state)
    resp = result["final_response"]
    print(f"AI:   {resp}")
    if "buyer_profile" in result:
        state["buyer_profile"] = result["buyer_profile"]
    state["conversation_history"].append({"role": "user", "content": q})
    state["conversation_history"].append({"role": "assistant", "content": resp})
    time.sleep(2)  # avoid hitting TPM limit between turns
