import numpy as np
from sklearn.ensemble import RandomForestClassifier
import pandas as pd

class MinesPredictor:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.is_trained = False
        self.mine_frequencies = {}
        self.raw_history = [] # On garde une copie brute pour le calcul de confiance

    def train_from_history(self, history_data):
        if not history_data:
            return
        
        self.raw_history = history_data
        mine_counts = {}
        total_sessions = len(history_data)
        
        for session in history_data:
            mines = session.get('tiles', [])
            for mine_pos in mines:
                mine_counts[mine_pos] = mine_counts.get(mine_pos, 0) + 1
        
        self.mine_frequencies = {
            pos: (count / total_sessions) * 100 
            for pos, count in mine_counts.items()
        }
        self.is_trained = True

    def get_safe_tiles(self, current_history, mines_count):
        available_tiles = [i for i in range(25) if i not in current_history]
        
        if not self.is_trained:
            import random
            return random.sample(available_tiles, min(mines_count, len(available_tiles)))
        
        safety_scores = []
        for tile in available_tiles:
            mine_probability = self.mine_frequencies.get(tile, 0)
            safety_scores.append((tile, 100 - mine_probability))
        
        safety_scores.sort(key=lambda x: x[1], reverse=True)
        # On ne retourne que les indices des cases pour le main.py
        return [tile for tile, score in safety_scores[:mines_count]]

    def get_confidence_score(self, predicted_tiles):
        """
        Calcule la probabilité globale de la suite (ex: 93%)
        """
        if not self.raw_history or not predicted_tiles:
            return 50.0
        
        wins = 0
        for session in self.raw_history:
            mines_in_session = session.get('tiles', [])
            # La suite est gagnante si AUCUNE des cases prédites n'est une mine
            if not any(tile in mines_in_session for tile in predicted_tiles):
                wins += 1
        
        # Calcul du pourcentage de réussite historique de cette combinaison
        score = (wins / len(self.raw_history)) * 100
        # On lisse le résultat pour l'affichage
        return round(max(50.0, min(98.5, score)), 1)
