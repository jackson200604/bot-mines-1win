import random
from collections import Counter


class Predictor:
    def __init__(self):
        self.safe_tiles = []

    def train_from_history(self, history_data):
        all_tiles = []

        for session in history_data:
            tiles = session.get("tiles", [])
            all_tiles.extend(tiles)

        counts = Counter(all_tiles)

        least_common = counts.most_common()

        sorted_tiles = [
            tile
            for tile, _ in least_common
        ]

        self.safe_tiles = sorted_tiles

    def predict_safe_tiles(self, count=3):
        if not self.safe_tiles:
            return random.sample(range(1, 26), count)

        prediction = self.safe_tiles[:count]

        while len(prediction) < count:
            rand_tile = random.randint(1, 25)

            if rand_tile not in prediction:
                prediction.append(rand_tile)

        return prediction
