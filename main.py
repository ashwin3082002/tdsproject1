from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "message": "Flask running on Vercel"}), 200

@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "Hello from Flask on Vercel!"}), 200

@app.route("/", methods=["POST"])
def handle_task():
    data = request.get_json(silent=True) or {}
    
    if data.get("secret") != "your-secret":
        return jsonify({"error": "Invalid secret"}), 403

    return jsonify({
        "status": "accepted",
        "task": data.get("task"),
        "round": data.get("round")
    }), 200