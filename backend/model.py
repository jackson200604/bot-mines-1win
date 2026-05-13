import numpy as np

class MinesPredictor:
    def __init__(self):
        self.is_trained = False
        self.mine_frequencies = {}
        self.raw_history = []

    def train_from_history(self, history_data):
        """Analyse l'historique pour calculer les fréquences."""
        if not history_data:
            return
        
        self.raw_history = history_data
        mine_counts = {}
        total_sessions = len(history_data)
        
        for session in history_data:
            # Utilisation de 'tiles' pour la cohérence
            mines = session.get('tiles', [])
            for mine_pos in mines:
                mine_counts[mine_pos] = mine_counts.get(mine_pos, 0) + 1
        
        self.mine_frequencies = {
            pos: (count / total_sessions) * 100 
            for pos, count in mine_counts.items()
        }
        self.is_trained = True

    def get_safe_tiles(self, current_history, mines_count):
        """Retourne les indices des cases les plus sûres [12, 5, 8]."""
        available_tiles = [i for i in range(25) if i not in current_history]
        
        if not self.is_trained:
            import random
            return random.sample(available_tiles, min(int(mines_count), len(available_tiles)))
        
        safety_scores = []
        for tile in available_tiles:
            mine_probability = self.mine_frequencies.get(tile, 0)
            safety_scores.append((tile, 100 - mine_probability))
        
        # Tri par sécurité décroissante
        safety_scores.sort(key=lambda x: x[1], reverse=True)
        
        return [tile for tile, score in safety_scores[:int(mines_count)]]

    def get_confidence_score(self, predicted_tiles):
        """Calcule le % de réussite global de la suite proposée."""
        if not self.raw_history or not predicted_tiles:
            return 50.0
        
        wins = 0
        for session in self.raw_history:
            mines_in_session = session.get('tiles', [])
            # Gagné si aucune mine n'est sur les cases prédites
            if not any(tile in mines_in_session for tile in predicted_tiles):
                wins += 1
        
        score = (wins / len(self.raw_history)) * 100
        return round(max(50.0, min(98.5, score)), 1)
