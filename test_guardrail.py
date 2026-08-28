import sys
from backend.agent.nodes import guardrail_node

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def run_tests():
    print("==================================================")
    print("GUARDRAIL VERIFICATION TESTS")
    print("==================================================")

    # Test Case 1: Empty structured results, hallucinated price in draft
    state_hallucinated_price = {
        "user_query": "What is the price of the 3 BHK unit?",
        "structured_results": [],
        "draft_response": "The 3 BHK unit is priced at ₹2,50,00,000 with premium fittings.",
    }
    result_1 = guardrail_node(state_hallucinated_price)
    print("\n--- TEST 1: Hallucinated Price (₹2,50,00,000) with Empty structured_results ---")
    print("Draft Response :", state_hallucinated_price["draft_response"])
    print("Guardrail OK   :", result_1["guardrail_ok"])
    print("Final Response :", result_1["final_response"])

    # Test Case 2: Empty structured results, hallucinated date/year in draft
    state_hallucinated_date = {
        "user_query": "When is the possession date for Tower A?",
        "structured_results": [],
        "draft_response": "Possession for Tower A is scheduled for December 2026.",
    }
    result_2 = guardrail_node(state_hallucinated_date)
    print("\n--- TEST 2: Hallucinated Year/Date (2026) with Empty structured_results ---")
    print("Draft Response :", state_hallucinated_date["draft_response"])
    print("Guardrail OK   :", result_2["guardrail_ok"])
    print("Final Response :", result_2["final_response"])

    # Test Case 3: Empty structured results, hallucinated crore/lakh phrase
    state_hallucinated_crore = {
        "user_query": "How much does a 2 BHK cost?",
        "structured_results": [],
        "draft_response": "Starting prices are around 1.5 Cr onwards.",
    }
    result_3 = guardrail_node(state_hallucinated_crore)
    print("\n--- TEST 3: Hallucinated Phrasing (1.5 Cr) with Empty structured_results ---")
    print("Draft Response :", state_hallucinated_crore["draft_response"])
    print("Guardrail OK   :", result_3["guardrail_ok"])
    print("Final Response :", result_3["final_response"])

    # Test Case 4: Valid structured results with matching verified figures
    state_valid = {
        "user_query": "What is the price and possession of unit A-101?",
        "structured_results": [{
            "unit_id": "A-101",
            "tower": "Tower A",
            "bhk": 2,
            "price_inr": 15000000.0,
            "possession_date": "2026-12-01",
            "status": "Available"
        }],
        "draft_response": "Unit A-101 is Available at ₹15000000.0 with possession on 2026-12-01.",
    }
    result_4 = guardrail_node(state_valid)
    print("\n--- TEST 4: Valid Structured Data (Verified Pass-Through) ---")
    print("Draft Response :", state_valid["draft_response"])
    print("Guardrail OK   :", result_4["guardrail_ok"])
    print("Final Response :", result_4["final_response"])
    print("\n==================================================")

if __name__ == "__main__":
    run_tests()
