import sys
from backend.agent.nodes import guardrail_node

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def run_tests():
    print("==================================================")
    print("EDGE CASE & GUARDRAIL TRICK VERIFICATION")
    print("==================================================")

    test_cases = [
        {
            "name": "1. Valid Structured",
            "query": "What is the price of the 3 BHK in Tower A?",
            "structured_results": [{'unit_id': 'A-502', 'bhk': 3, 'price_inr': 25000000.0, 'possession_date': '2026-12-01'}],
            "draft_response": "Unit A-502 is available for ₹25000000.0 with possession on 2026-12-01.",
            "expected_ok": True
        },
        {
            "name": "2. Leading Question (Brochure Price Trick)",
            "query": "Is the 3 BHK 1.4 Cr like the brochure says?",
            "structured_results": [{'unit_id': 'A-502', 'bhk': 3, 'price_inr': 25000000.0, 'possession_date': '2026-12-01'}],
            "draft_response": "The brochure indicates starting prices from 1.4 Cr, but A-502 is ₹25000000.0.",
            "expected_ok": False # Fails because '1.4 cr' is not verbatim in structured_results
        },
        {
            "name": "3. Hallucinated Unit (Doesn't exist)",
            "query": "Price of unit C-101?",
            "structured_results": [],
            "draft_response": "Unit C-101 is available for ₹18000000.0.",
            "expected_ok": False
        },
        {
            "name": "4. General Possession Date (From Brochure)",
            "query": "When is possession?",
            "structured_results": [],
            "draft_response": "Possession is planned through 2026-2027 according to the brochure.",
            "expected_ok": False # Fails because 2026 and 2027 are unverified by structured data
        },
        {
            "name": "5. Brochure Amenities (No numbers)",
            "query": "What are the amenities?",
            "structured_results": [],
            "draft_response": "Meridian Heights features a resort-style pool, clubhouse, and indoor games room.",
            "expected_ok": True
        },
        {
            "name": "6. Brochure Specs (Safe Numbers)",
            "query": "How large is the project?",
            "structured_results": [],
            "draft_response": "The project is spread across 6.2 acres.",
            "expected_ok": True # Passes because 6.2 is not a price or year
        },
        {
            "name": "7. Mixed Query (Valid)",
            "query": "Tell me the 4 BHK price and amenities.",
            "structured_results": [{'unit_id': 'A-1001', 'bhk': 4, 'price_inr': 38000000.0, 'possession_date': '2026-12-01'}],
            "draft_response": "A-1001 is ₹38000000.0. Amenities include a fully equipped clubhouse and 24x7 security.",
            "expected_ok": True
        },
        {
            "name": "8. Estimate a Price (Trick)",
            "query": "Estimate the price of a 5 BHK.",
            "structured_results": [],
            "draft_response": "Since a 4 BHK is 3.8 Cr, a 5 BHK would be around 5 Cr.",
            "expected_ok": False # Fails on '5 cr' and '3.8 cr'
        },
        {
            "name": "9. Brochure Specs (Safe text)",
            "query": "Is there EV charging?",
            "structured_results": [],
            "draft_response": "Yes, there are EV charging points in the basement.",
            "expected_ok": True
        },
        {
            "name": "10. Leading Price (Lower than actual)",
            "query": "I saw a 2 BHK for ₹12000000, can I book it?",
            "structured_results": [{'unit_id': 'A-101', 'bhk': 2, 'price_inr': 15000000.0, 'possession_date': '2026-12-01'}],
            "draft_response": "Yes, the 2 BHK is available for ₹12000000.",
            "expected_ok": False # Fails because ₹12000000 != 15000000.0
        },
        {
            "name": "11. Leading Date (Trick)",
            "query": "Can you confirm possession for Tower B is 2025?",
            "structured_results": [{'unit_id': 'B-101', 'bhk': 2, 'price_inr': 14500000.0, 'possession_date': '2027-06-01'}],
            "draft_response": "Possession for Tower B is expected in 2025.",
            "expected_ok": False # Fails because 2025 != 2027
        }
    ]

    all_passed = True
    for tc in test_cases:
        state = {
            "user_query": tc["query"],
            "structured_results": tc["structured_results"],
            "draft_response": tc["draft_response"]
        }
        res = guardrail_node(state)
        actual_ok = res["guardrail_ok"]
        
        status = "✅ PASS" if actual_ok == tc["expected_ok"] else "❌ FAIL"
        if not (actual_ok == tc["expected_ok"]):
            all_passed = False

        print(f"\n{status} | {tc['name']}")
        print(f"   Query: {tc['query']}")
        print(f"   Draft: {tc['draft_response']}")
        print(f"   Expected Guardrail OK: {tc['expected_ok']} | Actual: {actual_ok}")
        if not actual_ok:
            print(f"   Fallback triggered: {res['final_response']}")

    print("\n==================================================")
    if all_passed:
        print("🎉 ALL EDGE CASES HANDLED SUCCESSFULLY")
    else:
        print("⚠️ SOME EDGE CASES FAILED")

if __name__ == "__main__":
    run_tests()
