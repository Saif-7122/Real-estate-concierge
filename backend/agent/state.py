from typing import TypedDict, List, Dict, Any, Optional


class ConciergeState(TypedDict, total=False):
    user_query: str
    conversation_history: List[Dict[str, Any]]
    route: str
    structured_results: List[Dict[str, Any]]
    brochure_chunks: List[str]
    buyer_profile: Dict[str, Any]
    draft_response: str
    guardrail_ok: bool
    final_response: str
