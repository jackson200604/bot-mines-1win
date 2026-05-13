import numpy as np
from sklearn.ensemble import RandomForestClassifier

class MinesPredictor:
    def __init__(self):
        self.is_trained = False
        self.mine_frequencies = {}
        self.raw_history = []

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
        self.mine_frequencies = {pos: (count / total_sessions) * 100 for pos, count in mine_counts.items()}
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
        # CORRECTION : On renvoie uniquement l'index [12, 7, 5]
        return [tile for tile, score in safety_scores[:mines_count]]

    def get_confidence_score(self, predicted_tiles):
        if not self.raw_history or not predicted_tiles:
            return 50.0
        wins = sum(1 for s in self.raw_history if not any(t in s.get('tiles', []) for t in predicted_tiles))
        score = (wins / len(self.raw_history)) * 100
        return round(max(50.0, min(98.5, score)), 1)
