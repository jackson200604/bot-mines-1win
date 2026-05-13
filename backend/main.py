import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
from model import MinesPredictor

app = Flask(__name__)
CORS(app)

predictor = MinesPredictor()

# --- CONFIGURATION MONGODB ---
# Utilise la variable d'environnement MONGO_URI configurée dans Render
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://admin:<password>@bookhook.gurhu0q.mongodb.net/?retryWrites=true&w=majority&appName=Bookhook")

try:
    client = MongoClient(MONGO_URI)
    db = client['mines_bot_db']
    collection_train = db['training_sessions']
    # Test de connexion
    client.admin.command('ping')
    print("Connexion MongoDB réussie !")
except Exception as e:
    print(f"Erreur de connexion : {e}")

@app.route('/train', methods=['POST'])
def train():
    data = request.json
    mines = data.get('mines', [])
    if not mines:
        return jsonify({"error": "No mines provided"}), 400
    
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
def predict():
    data = request.json
    count = int(data.get('count', 3))

    all_sessions = list(collection_train.find())
    if len(all_sessions) < 2:
        return jsonify({
            "predictions": "12;7;17",
            "probability": "50%",
            "details": [
                {"tile": "12", "safety": "50.0%"},
                {"tile": "7", "safety": "50.0%"},
                {"tile": "17", "safety": "50.0%"}
            ]
        })

    # Entraîne le modèle avec l'historique
    history_data = [
        {"tiles": s.get("mines", []), "mines": s.get("count", 3)}
        for s in all_sessions
    ]
    predictor.train_from_history(history_data)

    # Récupère les cases déjà ouvertes
    current_history = data.get('current_history', [])
    safe_tiles = predictor.get_safe_tiles(current_history, count)

    # Formate la réponse avec les probabilités
    predictions_list = [str(tile) for tile, prob in safe_tiles]
    predictions_str = ";".join(predictions_list)
    
    # Calcule la probabilité moyenne
    avg_probability = sum(prob for _, prob in safe_tiles) / len(safe_tiles) if safe_tiles else 0
    probability_str = f"{int(round(avg_probability))}%"
    
    # Détails avec probabilités individuelles
    details = [
        {"tile": str(tile), "safety": f"{prob:.1f}%"}
        for tile, prob in safe_tiles
    ]

    return jsonify({
        "predictions": predictions_str,
        "probability": probability_str,
        "details": details
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    total = collection_train.count_documents({})
    return jsonify({"total_sessions": total})

@app.route('/get_training_history', methods=['GET'])
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
