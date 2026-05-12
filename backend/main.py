import os
import cv2
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

CSV_FILE = 'mines_data.csv'
UPLOAD_FOLDER = 'temp_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Création du fichier CSV s'il n'existe pas
if not os.path.exists(CSV_FILE):
    df = pd.DataFrame(columns=[f'cell_{i}' for i in range(25)])
    df.to_csv(CSV_FILE, index=False)

def save_mines(mines_list):
    if not mines_list: return
    df = pd.read_csv(CSV_FILE)
    row = [1 if i in mines_list else 0 for i in range(25)]
    df.loc[len(df)] = row
    df.to_csv(CSV_FILE, index=False)

# Route 1 : Enregistrement manuel via Overlay
@app.route('/train', methods=['POST'])
def train_manual():
    data = request.json
    mines = data.get('mines', [])
    save_mines(mines)
    return jsonify({"status": "success"})

# Route 2 : Prédiction intelligente
@app.route('/predict', methods=['POST'])
def predict():
    df = pd.read_csv(CSV_FILE)
    if len(df) < 5:
        # Valeurs par défaut si le bot n'a pas encore assez appris
        return jsonify({"predictions": [12, 14, 18]})
    
    # Cherche les cases avec le MOINS de mines
    probabilities = df.sum().sort_values()
    best_cells = [int(col.split('_')[1]) for col in probabilities.head(3).index]
    return jsonify({"predictions": best_cells})

# Route 3 : Analyse des vidéos XRecorder
@app.route('/process_video', methods=['POST'])
def process_video():
    if 'file' not in request.files:
        return jsonify({"error": "Aucun fichier envoyé"}), 400
    
    video = request.files['file']
    filename = secure_filename(video.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    video.save(path)

    cap = cv2.VideoCapture(path)
    sessions_found = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        # Analyse d'une image toutes les 30 frames
        if int(cap.get(cv2.CAP_PROP_POS_FRAMES)) % 30 == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            roi = gray[int(h*0.25):int(h*0.7), int(w*0.1):int(w*0.9)]
            _, thresh = cv2.threshold(roi, 180, 255, cv2.THRESH_BINARY)
            
            gh, gw = thresh.shape
            cell_h, cell_w = gh // 5, gw // 5
            current_mines = []
            
            for r in range(5):
                for c in range(5):
                    cell = thresh[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
                    if cv2.countNonZero(cell) > (cell_h * cell_w * 0.15):
                        current_mines.append(r * 5 + c)
            
            if len(current_mines) > 0:
                save_mines(current_mines)
                sessions_found += 1

    cap.release()
    os.remove(path) # Nettoie la vidéo après analyse
    return jsonify({"status": "finished", "sessions_found": sessions_found})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
