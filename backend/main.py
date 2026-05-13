import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from model import MinesPredictor

app = Flask(__name__)
CORS(app)
predictor = MinesPredictor()

MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://admin:votre_password@votre_cluster.mongodb.net/test")
client = MongoClient(MONGO_URI)
db = client['mines_bot_db']
collection_train = db['training_sessions']

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    count = int(data.get('count', 3))
    
    # Récupération de l'historique pour l'entraînement
    all_sessions = list(collection_train.find())
    history_data = [{"tiles": s.get("mines", [])} for s in all_sessions]
    predictor.train_from_history(history_data)

    # Récupération des prédictions
    safe_tiles = predictor.get_safe_tiles([], count)
    prob_value = predictor.get_confidence_score(safe_tiles)

    return jsonify({
        "predictions": safe_tiles,
        "probability": f"{prob_value}%"
    })

# ... garde tes autres routes (/train, /stats) comme elles sont ...

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
