import os
import pandas as pd
import cv2
import numpy as np
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

CSV_FILE = 'mines_data.csv'

# Création du fichier CSV s'il n'existe pas avec les colonnes cell_0 à cell_24
if not os.path.exists(CSV_FILE):
    columns = [f'cell_{i}' for i in range(25)]
    df = pd.DataFrame(columns=columns)
    df.to_csv(CSV_FILE, index=False)

@app.route('/train', methods=['POST'])
def train():
    data = request.json
    mines = data.get('mines', [])
    
    # Créer une ligne de 25 colonnes (0 pour vide, 1 pour mine)
    row = [0] * 25
    for m in mines:
        if 0 <= m < 25:
            row[m] = 1
            
    df_new = pd.DataFrame([row], columns=[f'cell_{i}' for i in range(25)])
    df_new.to_csv(CSV_FILE, mode='a', header=False, index=False)
    return jsonify({"status": "success"})

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    count = int(data.get('count', 3)) # Reçoit 1, 3 ou 5
    
    df = pd.read_csv(CSV_FILE)
    if len(df) < 3:
        # Si trop peu de données, on donne des coins au hasard
        return jsonify({"predictions": [0, 4, 20, 24, 12][:count]})
    
    # Calcul des probabilités : on prend les cases où il y a eu le MOINS de mines
    stats = df.sum().sort_values()
    best_cells = [int(col.split('_')[1]) for col in stats.head(count).index]
    
    return jsonify({"predictions": best_cells})

@app.route('/stats', methods=['GET'])
def get_stats():
    df = pd.read_csv(CSV_FILE)
    return jsonify({"total_sessions": len(df)})

@app.route('/download-database')
def download_db():
    return send_file(CSV_FILE, as_attachment=True)

@app.route('/process_video', methods=['POST'])
def process_video():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    
    file = request.files['file']
    path = os.path.join("temp_uploads", file.filename)
    file.save(path)
    
    cap = cv2.VideoCapture(path)
    sessions_count = 0
    
    # Analyse une frame sur 30
    frame_idx = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        if frame_idx % 30 == 0:
            # Conversion en noir et blanc pour détecter les croix blanches
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            
            # (Simplification logicielle ici pour l'exemple)
            # Dans un vrai usage, on analyserait les zones de la grille ici
            
        frame_idx += 1
    
    cap.release()
    os.remove(path)
    return jsonify({"sessions_found": sessions_count})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
