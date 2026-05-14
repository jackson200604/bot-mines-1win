"""
MinesPredictor — frequency-based safe cell predictor.

Wraps the same logic used in main.py's /predict route so it can be
imported, tested, or extended independently (e.g. with a real ML model).
"""

class MinesPredictor:
    def __init__(self):
        self.cell_counts = [0] * 25  # cumulative mine frequency per cell
        self.session_count = 0

    def add_session(self, mines: list[int]):
        """Record a completed game session.

        Args:
            mines: List of cell indices (0-24) where mines were located.
        """
        if not mines:
            return
        mines = [m for m in set(mines) if isinstance(m, int) and 0 <= m <= 24]
        for idx in mines:
            self.cell_counts[idx] += 1
        self.session_count += 1

    def get_safe_tiles(self, count: int = 3, exclude: list[int] = None) -> list[int]:
        """Return the `count` cells least likely to contain a mine.

        Args:
            count:   Number of safe cell predictions to return.
            exclude: Cell indices already revealed; skip these.

        Returns:
            List of cell indices sorted from safest to least safe.
        """
        exclude = set(exclude or [])
        available = [(i, self.cell_counts[i]) for i in range(25) if i not in exclude]
        available.sort(key=lambda x: x[1])  # ascending: fewest mines = safest
        return [cell for cell, _ in available[:count]]

    def from_mongo_sessions(self, sessions: list[dict]):
        """Populate predictor from a list of MongoDB session documents.

        Args:
            sessions: List of dicts with a 'grid' key (25-element 0/1 list).
        """
        self.cell_counts = [0] * 25
        self.session_count = 0
        for s in sessions:
            grid = s.get('grid', [])
            if len(grid) == 25:
                for idx, val in enumerate(grid):
                    self.cell_counts[idx] += val
                self.session_count += 1
