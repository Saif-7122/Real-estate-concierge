import os
import sys
import time

# Ensure project root is in sys.path so 'backend' package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, request, jsonify, make_response, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from backend.agent.graph import concierge_app

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")


# Set up Rate Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["30 per hour", "5 per minute"]
)

# Prometheus Metrics
REQUESTS_BY_ROUTE = Counter(
    'requests_by_route', 
    'Number of requests categorized by router route', 
    ['route']
)
GUARDRAIL_TRIGGERS = Counter(
    'guardrail_triggers', 
    'Number of times the guardrail intercepted a hallucination'
)
LATENCY = Histogram(
    'chat_request_latency_seconds', 
    'Latency of the /chat endpoint in seconds'
)


@app.route('/')
@limiter.exempt
def serve_frontend():
    """Serve the chat interface."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route('/health', methods=['GET'])
@limiter.exempt
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200


@app.route('/metrics', methods=['GET'])
@limiter.exempt
def metrics():
    """Prometheus metrics endpoint."""
    data = generate_latest()
    response = make_response(data)
    response.headers['Content-Type'] = CONTENT_TYPE_LATEST
    return response


@app.route('/chat', methods=['POST'])
@LATENCY.time()
def chat_endpoint():
    """
    Main chat endpoint to invoke the LangGraph agent.
    Expects JSON: {"user_query": str} or {"message": str}
    """
    data = request.get_json(silent=True) or {}
    user_query = (data.get("user_query") or data.get("message") or "").strip()
    
    if not user_query:
        return jsonify({"error": "user_query or message is required"}), 400

        
    if len(user_query) > 500:
        return jsonify({"error": "Message length exceeds max 500 characters"}), 400
        
    buyer_profile = data.get("buyer_profile", {})
    
    start_time = time.time()
    
    # Set up input state for LangGraph
    state_input = {
        "user_query": user_query,
        "buyer_profile": buyer_profile,
        "conversation_history": data.get("conversation_history", [])
    }
    
    try:
        final_state = concierge_app.invoke(state_input)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
    latency = time.time() - start_time
    
    route = final_state.get("route", "unknown")
    guardrail_ok = final_state.get("guardrail_ok", True)
    final_response = final_state.get("final_response", "")
    
    # Update metrics based on execution
    REQUESTS_BY_ROUTE.labels(route=route).inc()
    if not guardrail_ok:
        GUARDRAIL_TRIGGERS.inc()
        
    return jsonify({
        "response": final_response,
        "route": route,
        "latency": latency,
        "guardrail_ok": guardrail_ok
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
