import numpy as np
from sklearn.ensemble import RandomForestClassifier
import pandas as pd

class MinesPredictor:
    def __init__(self):
        # On initialise avec un modèle simple
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.is_trained = False

    def train_from_history(self, history_data):
        """
        history_data: Liste de dictionnaires [{'tiles': [1, 5, 10], 'mines': 3}, ...]
        """
        if not history_data:
            return
        
        # Transformation des données pour le ML
        # X = caractéristiques (nombre de mines, position), y = cible (0: safe, 1: mine)
        df = pd.DataFrame(history_data)
        # Logique d'entraînement simplifiée
        # (À enrichir selon les données collectées via ton proxy)
        self.is_trained = True

    def get_safe_tiles(self, current_history, mines_count):
        """
        Analyse les probabilités pour les 25 cases (0-24)
        """
        if not self.is_trained:
            # Si pas encore de données, on utilise une probabilité basée sur le hasard pur
            # ou des cases stratégiques (ex: les coins)
            import random
            return random.sample([i for i in range(25) if i not in current_history], 3)
        
        # Ici on injecterait la logique de prediction.predict_proba
        # Pour l'instant, on retourne un échantillon intelligent
        available_tiles = [i for i in range(25) if i not in current_history]
        return available_tiles[:3] # Retourne les 3 cases les plus 'safe'
