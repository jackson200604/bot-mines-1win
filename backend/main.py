import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timezone

from model import MinesPredictor, MinesTransformer

# ──────────────────────────────────────────────
# App + DB setup
# ──────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://jackson:mines2024@cluster0.mongodb.net/mines_bot?retryWrites=true&w=majority")
client = MongoClient(MONGO_URI)
db = client["mines_bot"]
games_col = db["games"]

# ──────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────
predictor = MinesPredictor()          # legacy frequency model
transformer = MinesTransformer(       # new transformer model
    grid_size=25,
    seq_len=10,
    weights_path=os.getenv("WEIGHTS_PATH", "weights.pt"),
)

# Preload legacy predictor history from DB
for doc in games_col.find().sort("timestamp", -1).limit(200):
    if "mines_positions" in doc:
        predictor.add_result(doc["mines_positions"])


# ──────────────────────────────────────────────
# Routes — Legacy
# ──────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "online",
        "message": "Mines Bot API is running",
        "endpoints": ["/predict", "/predict_v2", "/result", "/stats", "/health"],
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "transformer_ready": transformer.ready,
        "legacy_history_size": len(predictor.history),
    })


@app.route("/predict", methods=["POST"])
def predict():
    """Legacy frequency-based prediction."""
    data = request.get_json(silent=True) or {}
    grid_size = data.get("grid_size", 25)
    num_mines = data.get("num_mines", 3)
    num_safe = data.get("num_safe", 5)

    safe = predictor.predict_safe(grid_size=grid_size, num_mines=num_mines, num_safe=num_safe)

    return jsonify({
        "safe_positions": safe,
        "grid_size": grid_size,
        "num_mines": num_mines,
        "model": "frequency",
    })


@app.route("/result", methods=["POST"])
def result():
    """Record a game result (feeds both models)."""
    data = request.get_json(silent=True) or {}
    mines_positions = data.get("mines_positions", [])

    if not mines_positions:
        return jsonify({"error": "mines_positions is required"}), 400

    predictor.add_result(mines_positions)

    record = {
        "mines_positions": mines_positions,
        "timestamp": datetime.now(timezone.utc),
        "grid_size": data.get("grid_size", 25),
        "num_mines": data.get("num_mines", len(mines_positions)),
    }
    games_col.insert_one(record)

    return jsonify({"status": "recorded", "total_games": len(predictor.history)})


@app.route("/stats", methods=["GET"])
def stats():
    return jsonify(predictor.get_stats())


# ──────────────────────────────────────────────
# Routes — Transformer V2
# ──────────────────────────────────────────────
@app.route("/predict_v2", methods=["POST"])
def predict_v2():
    """Transformer-based prediction using recent game history."""
    data = request.get_json(silent=True) or {}
    num_safe = data.get("num_safe", 5)
    history_limit = data.get("history_limit", 50)

    # Pull recent history from DB
    docs = list(games_col.find().sort("timestamp", -1).limit(history_limit))
    history = [doc["mines_positions"] for doc in reversed(docs) if "mines_positions" in doc]

    if len(history) < 2:
        return jsonify({"error": "Not enough game history. Record more results via /result."}), 400

    result = transformer.predict_safe(history=history, num_safe=num_safe)

    return jsonify({
        "model": "transformer_v1",
        "history_used": len(history),
        **result,
    })


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
