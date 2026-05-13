import numpy as np
from sklearn.ensemble import RandomForestClassifier
import pandas as pd

class MinesPredictor:
    def __init__(self):
        # On initialise avec un modèle simple
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.is_trained = False
        self.mine_frequencies = {}

    def train_from_history(self, history_data):
        """
        history_data: Liste de dictionnaires [{'tiles': [1, 5, 10], 'mines': 3}, ...]
        """
        if not history_data:
            return
        
        # Calcul des fréquences de mines par position
        mine_counts = {}
        total_sessions = len(history_data)
        
        for session in history_data:
            mines = session.get('tiles', [])
            for mine_pos in mines:
                mine_counts[mine_pos] = mine_counts.get(mine_pos, 0) + 1
        
        # Conversion en probabilités (pourcentage)
        self.mine_frequencies = {
            pos: (count / total_sessions) * 100 
            for pos, count in mine_counts.items()
        }
        
        self.is_trained = True

    def get_safe_tiles(self, current_history, mines_count):
        """
        Retourne les cases les plus sûres avec leurs probabilités
        Retour: Liste de tuples (tile_index, safety_probability)
        """
        available_tiles = [i for i in range(25) if i not in current_history]
        
        if not self.is_trained or not self.mine_frequencies:
            # Si pas de données, probabilités par défaut
            import random
            tiles = random.sample(available_tiles, min(mines_count, len(available_tiles)))
            return [(tile, 50.0) for tile in tiles]
        
        # Calcul des probabilités de sécurité pour chaque case
        safety_scores = []
        for tile in available_tiles:
            mine_probability = self.mine_frequencies.get(tile, 0)
            safety_probability = 100 - mine_probability
            safety_scores.append((tile, safety_probability))
        
        # Tri par probabilité de sécurité (décroissant)
        safety_scores.sort(key=lambda x: x[1], reverse=True)
        
        return safety_scores[:mines_count]
