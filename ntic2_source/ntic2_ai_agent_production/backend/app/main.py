import os
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Flask, request, jsonify, make_response, Response # pyright: ignore[reportMissingImports]
from dotenv import load_dotenv # pyright: ignore[reportMissingImports]
import chromadb # pyright: ignore[reportMissingImports]

from app.agent.core import agent_run_streaming
from app.memory import clear_conversation

# Config
app = Flask(__name__)
project_root = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=project_root / '.env')
logging.basicConfig(level=logging.INFO)

# Rate limit simple
_rate_limit_store = defaultdict(list)
def check_rate_limit(ip):
    now = datetime.now()
    _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if now - t < timedelta(minutes=1)]
    if len(_rate_limit_store[ip]) >= 30: return False
    _rate_limit_store[ip].append(now)
    return True

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

@app.route("/api/chat", methods=["POST"])
def chat():
    client_ip = request.remote_addr or "unknown"
    if not check_rate_limit(client_ip): return jsonify({"error": "rate_limit"}), 429
    
    data = request.json
    if not data or "message" not in data: return jsonify({"error": "message manquant"}), 400
    
    full_reply = ""
    final_data = {}
    for chunk_json in agent_run_streaming(data["message"], data.get("user_id", "anon")):
        chunk = json.loads(chunk_json)
        if chunk["type"] == "content": full_reply += chunk["content"]
        elif chunk["type"] == "end": final_data = chunk["data"]
    
    if final_data: final_data["reply"] = full_reply
    return jsonify(final_data or {"reply": full_reply})

@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    data = request.json
    if not data or "message" not in data: return jsonify({"error": "message manquant"}), 400
    
    def generate():
        try:
            for chunk in agent_run_streaming(data["message"], data.get("user_id", "anon")):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            
    return Response(generate(), mimetype='text/event-stream')

@app.route("/api/chat/status", methods=["GET"])
def chat_status():
    try:
        from app.rag.pipeline import get_chromadb_path
        client = chromadb.PersistentClient(path=get_chromadb_path())
        collection = client.get_collection(name="website_content")
        count = len(collection.get()["ids"])
        return jsonify({"chunks": count, "connected": True, "status": "ok"})
    except:
        return jsonify({"chunks": 0, "connected": True, "status": "no_data"})

@app.route("/api/chat/clear", methods=["POST"])
def clear_chat():
    user_id = (request.json or {}).get("user_id", "anon")
    clear_conversation(user_id)
    return jsonify({"status": "success"})

@app.route("/", methods=["GET"])
def root():
    return jsonify({"status": "ok", "service": "ISTA NTIC AI Agent"})

@app.errorhandler(Exception)
def handle_exception(e):
    """Gestionnaire d'erreurs global pour éviter les 500 opaques"""
    logging.error(f"Erreur non gérée: {e}", exc_info=True)
    return jsonify({
        "error": "internal_error",
        "message": str(e),
        "type": type(e).__name__
    }), 200 # On retourne 200 pour que le frontend puisse lire l'erreur proprement

if __name__ == "__main__":
    # Désactivation du reloader pour éviter les boucles de redémarrage infinies sur Windows
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
