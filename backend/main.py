import os
import functools
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
CORS(app)

# --- RATE LIMITING ---
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per hour"],
    storage_uri="memory://"
)

# --- CONFIGURATION MONGODB ---
# Requires MONGO_URI environment variable — configure in Render dashboard
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError(
        "MONGO_URI environment variable is not set. "
        "Configure it in your Render dashboard."
    )

try:
    client = MongoClient(MONGO_URI)
    db = client['mines_bot_db']
    collection_train = db['training_sessions']
    client.admin.command('ping')
    print("Connexion MongoDB réussie !")
except Exception as e:
    raise RuntimeError(f"Erreur de connexion MongoDB : {e}")

# --- AUTHENTICATION ---
API_KEY = os.environ.get("API_KEY")

def require_api_key(f):
    """Requires X-API-Key header to match API_KEY env var.
    If API_KEY is not configured, auth is disabled (dev mode)."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not API_KEY:
            return f(*args, **kwargs)
        key = request.headers.get("X-API-Key", "")
        if key != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# --- ROUTES ---

@app.route('/train', methods=['POST'])
@require_api_key
@limiter.limit("60 per minute")
def train():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    mines = data.get('mines', [])

    if not mines:
        return jsonify({"error": "No mines provided"}), 400
    if not isinstance(mines, list):
        return jsonify({"error": "mines must be a list"}), 400

    # Deduplicate and validate each index
    mines = list(set(mines))
    if not all(isinstance(m, int) and 0 <= m <= 24 for m in mines):
        return jsonify({"error": "Each mine index must be an integer between 0 and 24"}), 400
    if len(mines) > 24:
        return jsonify({"error": "Too many mines (max 24)"}), 400

    doc = {
        "date": datetime.now(),
        "mines": mines,
        "count": len(mines),
        "grid": [1 if i in mines else 0 for i in range(25)]
    }
    collection_train.insert_one(doc)
    total = collection_train.count_documents({})
    return jsonify({"status": "success", "new_total": total})


@app.route('/predict', methods=['POST'])
@require_api_key
@limiter.limit("60 per minute")
def predict():
    data = request.json or {}
    try:
        count = int(data.get('count', 3))
    except (ValueError, TypeError):
        return jsonify({"error": "count must be an integer"}), 400

    if not (1 <= count <= 24):
        return jsonify({"error": "count must be between 1 and 24"}), 400

    total = collection_train.count_documents({})
    if total < 2:
        return jsonify({"predictions": [12, 7, 17, 2, 22][:count]})

    # Memory-efficient aggregation — avoids loading all documents into RAM
    pipeline = [
        {"$project": {"grid": 1}},
        {"$unwind": {"path": "$grid", "includeArrayIndex": "cellIndex"}},
        {"$group": {"_id": "$cellIndex", "total": {"$sum": "$grid"}}},
        {"$sort": {"total": 1}},  # ascending: least-frequent mines = safest cells
        {"$limit": count}
    ]
    results = list(collection_train.aggregate(pipeline))
    best_cells = [int(r["_id"]) for r in results]

    # Pad with remaining cells if aggregation returns fewer than requested
    if len(best_cells) < count:
        remaining = [c for c in range(25) if c not in best_cells]
        best_cells += remaining[:count - len(best_cells)]

    return jsonify({"predictions": best_cells})


@app.route('/stats', methods=['GET'])
@require_api_key
def get_stats():
    total = collection_train.count_documents({})
    return jsonify({"total_sessions": total})


@app.route('/get_training_history', methods=['GET'])
@require_api_key
def get_training_history():
    logs = list(collection_train.find().sort("date", -1).limit(10))
    formatted = []
    for l in logs:
        formatted.append({
            "date": l['date'].strftime("%H:%M"),
            "mines_indices": str(l['mines']),
            "count": l['count']
        })
    return jsonify(formatted)


@app.route('/process_video', methods=['POST'])
@require_api_key
@limiter.limit("10 per minute")
def process_video():
    """
    Video scanning endpoint — not yet implemented.
    To implement: extract frames with OpenCV, detect mine positions via
    image recognition, then insert results via the /train logic.
    """
    return jsonify({
        "status": "not_implemented",
        "message": (
            "La détection automatique par vidéo n'est pas encore disponible. "
            "Utilisez le mode entraînement manuel pour enregistrer les mines."
        )
    }), 501


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
