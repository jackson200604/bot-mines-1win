import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION MONGODB ---
# REMPLACE <db_password> PAR TON VRAI MOT DE PASSE CI-DESSOUS
MONGO_URI = "mongodb+srv://admin:<jairu$06>@bookhook.gurhu0q.mongodb.net/?retryWrites=true&w=majority&appName=Bookhook"

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
        return jsonify({"predictions": [12, 7, 17, 2, 22][:count]})

    counts = [0] * 25
    for s in all_sessions:
        grid = s.get('grid', [0]*25)
        for idx, val in enumerate(grid):
            counts[idx] += val
            
    indexed_counts = list(enumerate(counts))
    indexed_counts.sort(key=lambda x: x[1])
    best_cells = [x[0] for x in indexed_counts[:count]]
    
    return jsonify({"predictions": best_cells})

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
    app.run(host='0.0.0.0', port=port)    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
