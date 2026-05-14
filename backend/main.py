import os
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from model import Predictor

app = Flask(__name__)

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://bot-mines-frontend.vercel.app"
)

CORS(app, resources={
    r"/*": {
        "origins": [FRONTEND_URL]
    }
})

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000
)

try:
    client.server_info()
except Exception:
    raise Exception("MongoDB inaccessible")


db = client["mines"]
collection_train = db["train"]
collection_predictions = db["predictions"]

predictor = Predictor()


def load_training_data():
    sessions = list(collection_train.find())

    history_data = [
        {
            "tiles": s.get("tiles", [])
        }
        for s in sessions
    ]

    predictor.train_from_history(history_data)


load_training_data()


@app.route('/health')
def health():
    return jsonify({
        "status": "ok"
    })


@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "error": "JSON invalide"
            }), 400

        count = int(data.get('count', 3))

        if count < 1 or count > 10:
            return jsonify({
                "error": "count doit être entre 1 et 10"
            }), 400

        prediction = predictor.predict_safe_tiles(count)

        collection_predictions.insert_one({
            "prediction": prediction
        })

        return jsonify({
            "success": True,
            "prediction": prediction
        })

    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
