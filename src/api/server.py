import os
import json
import uuid
from dotenv import load_dotenv
basedir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
load_dotenv(os.path.join(basedir, '.env'))

from flask import Flask, request, jsonify, send_from_directory

from src.core.intent_classifier import IntentClassifier
from src.core.retrieval import RetrievalEngine
from src.core.generation import Generator
from src.core.trust_gate import TrustGate
from src.core.safety_detector import SafetyDetector

app = Flask(__name__, static_folder="static")

# In-memory store for session states (Loop Breaker support)
SESSIONS = {}

# Initialize pipeline components
classifier = IntentClassifier()
retriever = RetrievalEngine(index_path="models/retrieval/faiss.index")
safety_detector = SafetyDetector()
trust_gate = TrustGate(confidence_threshold=0.6)

provider = os.environ.get("GENERATOR_PROVIDER", "gemini").lower()
has_api_key = False
if provider == "openai":
    has_api_key = bool(os.environ.get('OPENAI_API_KEY'))
else:
    has_api_key = bool(os.environ.get('GEMINI_API_KEY'))

generator = None
if has_api_key:
    try:
        generator = Generator()
    except Exception as e:
        print(f"Error initializing generator: {e}")
        import traceback
        traceback.print_exc()

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(app.static_folder, path)

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    session_id = data.get("session_id")
    user_message = data.get("message", "")
    
    if not session_id or session_id not in SESSIONS:
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = {
            "history": [],
            "loop_state": {
                "deep_analysis_attempts": 0,
                "issue_persists": False,
                "repeated_complaints": 0
            }
        }
        
    session = SESSIONS[session_id]
    
    # 1. Update Conversation Context
    # We construct a mock "thread" object for the pipeline
    session["history"].append({"inbound": True, "text_clean": user_message})
    
    # Check if this is a repeated complaint by simple heuristic
    # (If the user sends multiple messages, it increases repeated complaints)
    if len(session["history"]) > 2:
        session["loop_state"]["repeated_complaints"] += 1
        session["loop_state"]["issue_persists"] = True
        
    mock_tweets = {}
    for idx, msg in enumerate(session["history"]):
        mock_tweets[str(idx)] = {
            "inbound": msg["inbound"],
            "text_clean": msg["text_clean"]
        }
        
    query_conversation = {
        "root_tweet_id": session_id,
        "tweets": mock_tweets
    }
    
    # 2. Safety Detection
    safety_pred = safety_detector.evaluate(query_conversation)
    
    # 3. Intent Classification
    intent_res = classifier.predict(query_conversation)
    intent_pred = intent_res["primary_intent"]
    confidence = intent_res["confidence"]
    
    # 4. Retrieval
    retrieval_res = retriever.retrieve(query_conversation, intent_pred, top_k=3)
    retrieved_precedents = retrieval_res.get("candidates", [])
    
    # 5. Generation
    capability_state = {"mock": "UNKNOWN"} # Track A constraint
    
    if generator and has_api_key:
        gen_context = {
            "query_conversation": query_conversation,
            "predicted_intent": intent_pred,
            "intent_confidence": confidence,
            "retrieved_precedents": retrieved_precedents,
            "capability_state": capability_state
        }
        gen_result = generator.generate_response(gen_context)
        demo_mode = False
    else:
        # LLM Unavailable Mode (Demo)
        gen_result = {
            "generated_response": "I want to make sure this is handled correctly. Could you please DM us with your order details so our specialized team can look into it? [AI Generated]",
            "claims_made": [],
            "actions_implied": [],
            "unsupported_claims_removed": False,
            "routed_to_deep_analysis": False
        }
        demo_mode = True
        
    # 6. Trust Gate
    tg_context = {
        "query_conversation": query_conversation,
        "predicted_intent": intent_pred,
        "intent_confidence": confidence,
        "retrieved_precedents": retrieved_precedents,
        "capability_state": capability_state,
        "safety_legal_concern": safety_pred == "SAFETY_CONCERN",
        "explicit_human_request": "human" in user_message.lower() or "representative" in user_message.lower(),
        "frustration_trajectory": "UNKNOWN"
    }
    
    tg_decision = trust_gate.evaluate(tg_context, session["loop_state"], gen_result)
    
    # Update loop state based on Trust Gate decision
    if tg_decision["tier"] == "DEEP_ANALYSIS":
        session["loop_state"]["deep_analysis_attempts"] += 1
    elif tg_decision["tier"] == "HUMAN_ESCALATION":
        # Reset after escalation for demo purposes
        session["loop_state"]["deep_analysis_attempts"] = 0
        session["loop_state"]["repeated_complaints"] = 0
        session["loop_state"]["issue_persists"] = False
        
    final_response = gen_result.get("generated_response", "")
    
    if tg_decision["tier"] == "HUMAN_ESCALATION":
        final_response = "I am escalating this immediately to a human specialist who will review your account and follow up with you. [AI Generated]"
        
    session["history"].append({"inbound": False, "text_clean": final_response})

    # Prepare detailed evidence for the UI Panel
    evidence = []
    seen_ids = set()
    for p in retrieved_precedents:
        if len(evidence) >= 3:
            break
        pid = p.get('precedent_id', '')
        if pid not in seen_ids:
            seen_ids.add(pid)
            evidence.append({
                "intent": p.get('precedent_intent', 'Unknown'),
                "status": p.get('outcome_status', 'UNKNOWN').replace('_', ' ').capitalize() + " precedent",
                "similarity": p.get('final_retrieval_score', 0.0)
            })

    return jsonify({
        "session_id": session_id,
        "response": final_response,
        "demo_mode": demo_mode,
        "metadata": {
            "intent": intent_pred,
            "confidence": f"{confidence:.2f}",
            "trust_decision": tg_decision["tier"],
            "capability": "UNKNOWN",
            "safety": safety_pred,
            "evidence": evidence,
            "provider": gen_result.get("provider", "none"),
            "model": gen_result.get("model", "none")
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
