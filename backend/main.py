import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
from model import MinesPredictor

app = Flask(__name__)
CORS(app)
predictor = MinesPredictor()

MONGO_URI = os.environ.get("MONGO_URI", "ton_lien_mongodb")
client = MongoClient(MONGO_URI)
db = client['mines_bot_db']
collection_train = db['training_sessions']

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    count = int(data.get('count', 3))
    
    all_sessions = list(collection_train.find())
    # Synchronisation des noms de clés : on utilise 'tiles'
    history_data = [{"tiles": s.get("tiles", [])} for s in all_sessions]
    predictor.train_from_history(history_data)

    safe_tiles = predictor.get_safe_tiles([], count)
    prob_value = predictor.get_confidence_score(safe_tiles)

    return jsonify({
        "predictions": safe_tiles,
        "probability": f"{prob_value}%"
    })

@app.route('/train', methods=['POST'])
def train():
    data = request.json
    mines = data.get('mines', [])
    if not mines: return jsonify({"error": "No mines"}), 400
    
    doc = {"date": datetime.now(), "tiles": mines, "count": len(mines)}
    collection_train.insert_one(doc)
    return jsonify({"status": "success", "new_total": collection_train.count_documents({})})

@app.route('/stats', methods=['GET'])
def get_stats():
    return jsonify({"total_sessions": collection_train.count_documents({})})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
