import os
import re
from typing import Dict, Any, List
from dotenv import load_dotenv
from groq import Groq

from backend.agent.state import ConciergeState
from backend.agent.prompts import ROUTER_SYSTEM_PROMPT, GENERATION_SYSTEM_PROMPT
from backend.retrieval.structured_store import query_units
from backend.retrieval.vector_store import get_brochure_retriever

load_dotenv()


def get_groq_client() -> Groq:
    """Helper to instantiate Groq client with API key."""
    api_key = os.getenv("GROQ_API_KEY")
    return Groq(api_key=api_key)


def router_node(state: ConciergeState) -> Dict[str, Any]:
    """
    Classifies the user query using Groq's llama-3.3-70b-versatile at temperature 0
    into 'structured', 'brochure', or 'both'. Falls back to intent heuristic if Groq key is absent.
    """
    user_query = state.get("user_query", "")
    api_key = os.getenv("GROQ_API_KEY")

    if api_key:
        try:
            client = get_groq_client()
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_query},
                ],
                temperature=0.0,
            )
            raw_route = response.choices[0].message.content.strip().lower()
            if "both" in raw_route:
                return {"route": "both"}
            elif "structured" in raw_route:
                return {"route": "structured"}
            elif "brochure" in raw_route:
                return {"route": "brochure"}
        except Exception:
            pass

    # Heuristic fallback for offline/local execution
    lower_q = user_query.lower()
    has_structured = any(k in lower_q for k in ["price", "cost", "possession", "available", "unit", "floor", "bhk", "rate", "sqft", "tower"])
    # 'builder', 'developer', 'reputation', 'known', 'company' are brochure-only signals
    has_brochure = any(k in lower_q for k in [
        "amenit", "location", "pool", "gym", "clubhouse", "spec",
        "developer", "park", "sports", "brochure", "builder",
        "reputation", "well known", "well-known", "company", "established",
    ])

    if has_structured and has_brochure:
        route = "both"
    elif has_structured:
        route = "structured"
    elif has_brochure:
        route = "brochure"
    else:
        route = "both"

    # Extract constraints from entire conversation history and current query
    buyer_profile = state.get("buyer_profile") or {}
    history = state.get("conversation_history", [])

    messages_to_process = [msg.get("content", "") for msg in history if msg.get("role") == "user"]
    messages_to_process.append(user_query)

    for content in messages_to_process:
        if not content:
            continue
        bhk_match = re.search(r'(\d+)\s*bhk', content, re.IGNORECASE)
        if bhk_match:
            try:
                buyer_profile["bhk"] = int(bhk_match.group(1))
            except ValueError:
                pass

        budget_match = re.search(
            r'(?:under|less than|budget of)\s*.*?(\d+(?:\.\d+)?)\s*(k|cr|crore|lakh)',
            content, re.IGNORECASE
        )
        if budget_match:
            pass  # placeholder for future budget extraction

    return {"route": route, "buyer_profile": buyer_profile}


def structured_retrieval_node(state: ConciergeState) -> Dict[str, Any]:
    """
    Retrieves matching units from SQLite inventory store using buyer_profile filters
    or query extraction.
    """
    user_query = state.get("user_query", "")
    buyer_profile = state.get("buyer_profile") or {}
    bhk = buyer_profile.get("bhk")
    max_price = buyer_profile.get("max_price")
    tower = buyer_profile.get("tower")

    results = query_units(bhk=bhk, max_price=max_price, tower=tower)
    return {"structured_results": results, "buyer_profile": buyer_profile}


def brochure_retrieval_node(state: ConciergeState) -> Dict[str, Any]:
    """
    Retrieves relevant brochure chunks from Astra DB vector store and extracts page_content list.
    """
    user_query = state.get("user_query", "")
    try:
        retriever = get_brochure_retriever(k=4)
        docs = retriever.invoke(user_query)
        chunks = [doc.page_content for doc in docs]
    except Exception:
        chunks = []

    return {"brochure_chunks": chunks}


def generation_node(state: ConciergeState) -> Dict[str, Any]:
    """
    Formats the generation prompt with structured data and brochure data,
    and calls Groq to generate a response.
    """
    structured_results = state.get("structured_results", [])
    brochure_chunks = state.get("brochure_chunks", [])
    user_query = state.get("user_query", "")
    api_key = os.getenv("GROQ_API_KEY")

    structured_data_str = "\n".join(str(res) for res in structured_results) if structured_results else "No structured data available."
    brochure_data_str = "\n\n".join(brochure_chunks) if brochure_chunks else "No brochure data available."

    if api_key:
        try:
            client = get_groq_client()
            sys_prompt = GENERATION_SYSTEM_PROMPT.format(
                structured_data=structured_data_str,
                brochure_data=brochure_data_str
            )

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_query},
                ],
                temperature=0.0,
            )

            draft = response.choices[0].message.content
            return {"draft_response": draft}
        except Exception as exc:
            import sys as _sys
            print(f"[generation_node] Groq call failed: {exc}", file=_sys.stderr)
            # Fall through to offline synthesiser — do NOT silently produce a data dump

    # -------------------------------------------------------------------
    # Offline / API-unavailable fallback.
    # IMPORTANT: answer the ACTUAL question, do not just dump retrieved data.
    # We inspect user_query to pick the most relevant subset and form a
    # direct sentence rather than a verbatim raw list.
    # -------------------------------------------------------------------
    route = state.get("route", "both")
    lower_q = user_query.lower()

    # Questions about counts / availability → summarise structured data
    is_count_question = any(k in lower_q for k in ["how many", "count", "number of", "how much"])
    # Questions about builder / developer / reputation → brochure only
    is_builder_question = any(k in lower_q for k in ["builder", "developer", "who built", "reputation", "well known", "well-known", "company", "established"])
    # Follow-up subjective questions that reference prior context
    is_subjective = any(k in lower_q for k in ["is he", "is she", "is it", "is the", "are they", "would you", "do you think", "reliable", "trustworthy"])

    if is_builder_question or (is_subjective and not structured_results):
        # Pure brochure question — answer only from brochure chunks
        if brochure_chunks:
            relevant = " ".join(brochure_chunks[:2])
            draft = (
                f"Based on the project brochure: {relevant}\n\n"
                "Note: I can only share what's stated in the brochure material. "
                "For independent verification of the developer's track record, I'd recommend checking RERA or speaking with our sales team."
            )
        else:
            draft = "I don't have developer or builder details in the loaded brochure data at the moment. Would you like me to connect you with our sales team?"

    elif is_count_question and structured_results:
        available = [u for u in structured_results if str(u.get("status", "")).lower() == "available"]
        count = len(available) if available else len(structured_results)
        bhk_types = sorted(set(u["bhk"] for u in structured_results))
        prices = [u["price_inr"] for u in structured_results if u.get("price_inr")]
        price_note = ""
        if prices:
            price_note = f", priced between ₹{min(prices):,} and ₹{max(prices):,}"
        draft = (
            f"There are currently {count} unit(s) available"
            + (f" in {bhk_types} BHK configurations" if bhk_types else "")
            + price_note + ". "
            "Would you like details on any specific configuration?"
        )

    elif structured_results and not brochure_chunks:
        available = [u for u in structured_results if str(u.get("status", "")).lower() == "available"]
        count = len(available) if available else len(structured_results)
        bhk_types = sorted(set(u["bhk"] for u in structured_results))
        unit_strs = [
            f"Unit {u['unit_id']} ({u['bhk']} BHK, {u['tower']}, Floor {u['floor']}, "
            f"{u['area_sqft']} sq.ft, ₹{u['price_inr']:,}, possession {u['possession_date']}) [{u['status']}]"
            for u in structured_results
        ]
        draft = (
            f"Found {count} matching unit(s) in {bhk_types} BHK configurations:\n"
            + "\n".join(unit_strs)
        )

    elif brochure_chunks and not structured_results:
        draft = " ".join(brochure_chunks[:2])

    elif structured_results and brochure_chunks:
        # Mixed question — give a concise summary, not a raw dump
        available = [u for u in structured_results if str(u.get("status", "")).lower() == "available"]
        count = len(available) if available else len(structured_results)
        bhk_types = sorted(set(u["bhk"] for u in structured_results))
        prices = [u["price_inr"] for u in structured_results if u.get("price_inr")]
        price_note = f", ranging from ₹{min(prices):,} to ₹{max(prices):,}" if prices else ""
        brochure_summary = brochure_chunks[0] if brochure_chunks else ""
        draft = (
            f"{count} unit(s) available in {bhk_types} BHK configurations{price_note}.\n\n"
            f"From the brochure: {brochure_summary}"
        )

    else:
        if route == "brochure":
            draft = "I don't have brochure details loaded at the moment. Would you like me to connect you with our sales team for project information?"
        else:
            draft = "I could not find any available units matching that criteria in our real-time inventory. Would you like me to connect you with our sales team for more options?"

    return {"draft_response": draft}



def guardrail_node(state: ConciergeState) -> Dict[str, Any]:
    """
    Regex-checks the draft response for currency figures, prices (including Cr/Lakh),
    and dates not present in structured_results.
    If unauthorized figures/dates are found, replaces response with a safe fallback.
    """
    draft_response = state.get("draft_response", "")
    structured_results = state.get("structured_results", [])
    brochure_chunks = state.get("brochure_chunks", [])

    # Extract all valid text tokens from structured_results and brochure_chunks to cross-check
    valid_values = []
    for res in structured_results:
        for val in res.values():
            valid_values.append(str(val).lower().replace(",", ""))
            
    for chunk in brochure_chunks:
        valid_values.append(str(chunk).lower().replace(",", ""))
        
    valid_text = " ".join(valid_values)

    clean_draft = draft_response.lower()

    violation = False

    # 1. Check for currency symbols followed by numbers (e.g., ₹25000000, Rs. 1.5, INR 50000)
    currency_matches = re.findall(r'(?:₹|rs\.?|inr|\$)\s*[\d,]+(?:\.\d+)?', clean_draft)
    if currency_matches:
        for match in currency_matches:
            num = re.sub(r'[^\d.]', '', match)
            if num and num not in valid_text:
                violation = True
                break

    # 2. Check for Indian numbering units (e.g. 1.5 cr, 2.5 crore, 85 lakhs)
    if not violation:
        unit_matches = re.findall(r'\b\d+(?:\.\d+)?\s*(?:cr|crore|crores|lakh|lakhs)\b', clean_draft)
        for match in unit_matches:
            num = re.sub(r'[^\d.]', '', match)
            if num and num not in valid_text:
                violation = True
                break

    # 3. Check for years and dates (e.g. 2024-2030)
    if not violation:
        dates = re.findall(r'\b(202[0-9]|203[0-9])\b', clean_draft)
        for date in dates:
            if date not in valid_text:
                violation = True
                break

    if violation:
        return {
            "guardrail_ok": False,
            "final_response": "I don't have the verified pricing or possession details for that query on hand. Would you like me to connect you with our sales team for exact figures?"
        }

    return {
        "guardrail_ok": True,
        "final_response": draft_response
    }

