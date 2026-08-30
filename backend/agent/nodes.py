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
    Classifies the user query using Groq into 'greeting', 'structured', 'brochure', or 'both'.
    Falls back to deterministic intent heuristics if Groq call fails.
    """
    user_query = state.get("user_query", "")
    api_key = os.getenv("GROQ_API_KEY")
    route = None

    # Check greetings / small talk first via quick heuristic or LLM
    lower_q = user_query.lower().strip()
    is_simple_greeting = bool(re.match(r'^(hi|hello|hey|good morning|good afternoon|good evening|thanks|thank you|bye|goodbye)[!.,\s]*$', lower_q))
    if is_simple_greeting:
        route = "greeting"

    if not route and api_key:
        try:
            client = get_groq_client()
            response = client.chat.completions.create(
                model=os.getenv("GROQ_MODEL", "groq/compound-mini"),
                messages=[
                    {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_query},
                ],
                temperature=0.0,
            )
            raw_route = response.choices[0].message.content.strip().lower()
            if "greeting" in raw_route:
                route = "greeting"
            elif "both" in raw_route:
                route = "both"
            elif "structured" in raw_route:
                route = "structured"
            elif "brochure" in raw_route:
                route = "brochure"
        except Exception as exc:
            import sys as _sys
            print(f"[router_node] Router LLM call failed: {exc}", file=_sys.stderr)

    if not route:
        # Heuristic fallback
        has_structured = any(k in lower_q for k in [
            "price", "cost", "possession", "available", "unit", "floor",
            "bhk", "rate", "sqft", "tower", "facing", "inventory", "ready"
        ])
        has_brochure = any(k in lower_q for k in [
            "amenit", "location", "pool", "gym", "clubhouse", "spec",
            "developer", "park", "sports", "brochure", "builder",
            "reputation", "well known", "well-known", "company", "established",
            "who built", "history", "track record"
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

        tower_match = re.search(r'tower\s*([ab])\b', content, re.IGNORECASE)
        if tower_match:
            buyer_profile["tower"] = f"Tower {tower_match.group(1).upper()}"

    return {"route": route, "buyer_profile": buyer_profile}


def structured_retrieval_node(state: ConciergeState) -> Dict[str, Any]:
    """
    Retrieves matching units from SQLite inventory store using buyer_profile filters.
    """
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
    Generates a natural, conversational response suitable for TTS.
    Calls Groq with GENERATION_SYSTEM_PROMPT and current user query,
    or uses a query-aware conversational fallback.
    """
    route = state.get("route", "both")
    user_query = state.get("user_query", "")
    structured_results = state.get("structured_results", [])
    brochure_chunks = state.get("brochure_chunks", [])
    api_key = os.getenv("GROQ_API_KEY")

    # Fast path for pure greetings / pleasantries
    if route == "greeting":
        lower_q = user_query.lower()
        if any(k in lower_q for k in ["thanks", "thank you"]):
            return {"draft_response": "You're welcome! Feel free to ask if you'd like to explore any units, pricing, or amenities."}
        return {"draft_response": "Hello! Welcome to Meridian Heights. How can I help you today with our available units, amenities, or pricing?"}

    structured_data_str = "\n".join(str(res) for res in structured_results) if structured_results else "No structured units found matching current criteria."
    brochure_data_str = "\n\n".join(brochure_chunks) if brochure_chunks else "No brochure data available."

    if api_key:
        try:
            client = get_groq_client()
            sys_prompt = GENERATION_SYSTEM_PROMPT.format(
                structured_data=structured_data_str,
                brochure_data=brochure_data_str
            )

            response = client.chat.completions.create(
                model=os.getenv("GROQ_MODEL", "groq/compound-mini"),
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_query},
                ],
                temperature=0.2,
            )

            draft = response.choices[0].message.content
            if draft:
                return {"draft_response": draft.strip()}
        except Exception as exc:
            import sys as _sys
            print(f"[generation_node] Groq call failed: {exc}", file=_sys.stderr)

    # -------------------------------------------------------------------
    # Conversational Fallback Synthesiser (voice-ready & query-focused)
    # -------------------------------------------------------------------
    lower_q = user_query.lower()

    # 1. Attributes not present in schema (e.g. facing, vastu)
    if "facing" in lower_q or "vastu" in lower_q or "direction" in lower_q:
        if structured_results:
            bhk_val = state.get("buyer_profile", {}).get("bhk")
            count = len(structured_results)
            bhk_text = f"{bhk_val} BHK " if bhk_val else ""
            draft = (
                f"We currently have {count} {bhk_text}unit(s) available in our inventory, "
                "though our current listing records don't specify the exact facing direction. "
                "I'd be happy to connect you with our sales advisor to verify specific East-facing units for you."
            )
        else:
            draft = "Our current inventory records do not list the facing direction for individual units. Would you like me to connect you with our sales team for detailed floor and facing plans?"
        return {"draft_response": draft}

    # 2. Builder / Developer specific queries
    if any(k in lower_q for k in ["who is the builder", "developer", "who built"]):
        draft = "Meridian Heights is developed by Skyline Developers, an established real estate firm active in Hyderabad with over a decade of experience across the Financial District and Gachibowli."
        return {"draft_response": draft}

    # 3. Subjective / Reputation questions
    if any(k in lower_q for k in ["well known", "well-known", "reputation", "track record", "reliable"]):
        draft = "Yes, Skyline Developers has been developing premium residential and commercial communities in Hyderabad for over ten years, known particularly for quality construction and timely delivery. For third-party project registration details, we always encourage checking their official RERA filings."
        return {"draft_response": draft}

    # 4. Inventory counts and pricing summaries
    if any(k in lower_q for k in ["how many", "count", "available now", "units are available"]):
        if structured_results:
            count = len(structured_results)
            bhk_types = sorted(set(u["bhk"] for u in structured_results))
            bhk_str = ", ".join(f"{b}" for b in bhk_types)
            prices = [u["price_inr"] for u in structured_results if u.get("price_inr")]
            price_min = f"₹{min(prices)/10000000:.2f} Cr" if prices else "competitive rates"
            draft = f"We currently have {count} units available across {bhk_str} BHK configurations, starting from {price_min}. Would you like more details on a specific BHK type or tower?"
        else:
            draft = "We don't currently have active units matching those exact filters in our database. Would you like to check other configurations or towers?"
        return {"draft_response": draft}

    # 5. Tower-specific pricing / single unit queries
    if "tower a" in lower_q or "tower b" in lower_q or "price" in lower_q:
        if structured_results:
            prices = [u["price_inr"] for u in structured_results if u.get("price_inr")]
            if prices:
                if len(prices) == 1:
                    draft = f"The price for this unit is ₹{prices[0]:,}. It comes with verified possession details in our inventory."
                else:
                    draft = f"Units matching your criteria are priced between ₹{min(prices):,} and ₹{max(prices):,}. Let me know if you'd like the exact floor-by-floor breakdown."
            else:
                draft = "I don't have verified pricing details for that specific tower configuration on hand. I can connect you with our sales team for exact figures."
        else:
            draft = "I don't have the verified pricing or possession details for that query on hand. Would you like me to connect you with our sales team for exact figures?"
        return {"draft_response": draft}

    # 6. Default conversational response
    if brochure_chunks:
        draft = "Based on our project records, Meridian Heights offers modern residences with resort-style amenities in Hyderabad's Financial District. Would you like to know more about the clubhouse, location, or available apartments?"
    else:
        draft = "I'm here to help with all details on Meridian Heights. Feel free to ask about our available 2, 3, and 4 BHK units, pricing, or project amenities."

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

