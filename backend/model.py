import random
import math
import torch
import torch.nn as nn
import numpy as np
from collections import Counter


# ──────────────────────────────────────────────
# LEGACY: Frequency-based predictor (backward compat)
# ──────────────────────────────────────────────
class MinesPredictor:
    def __init__(self):
        self.history = []

    def add_result(self, mines_positions: list):
        self.history.append(mines_positions)

    def predict_safe(self, grid_size: int = 25, num_mines: int = 3, num_safe: int = 5) -> list:
        if not self.history:
            all_positions = list(range(1, grid_size + 1))
            random.shuffle(all_positions)
            return sorted(all_positions[:num_safe])

        flat = [pos for game in self.history for pos in game]
        freq = Counter(flat)

        scored = []
        for i in range(1, grid_size + 1):
            scored.append((i, freq.get(i, 0)))

        scored.sort(key=lambda x: x[1])
        safe = [pos for pos, _ in scored[:num_safe]]
        return sorted(safe)

    def get_stats(self) -> dict:
        if not self.history:
            return {"total_games": 0, "most_common_mines": [], "least_common_positions": []}

        flat = [pos for game in self.history for pos in game]
        freq = Counter(flat)

        return {
            "total_games": len(self.history),
            "most_common_mines": freq.most_common(5),
            "least_common_positions": freq.most_common()[:-6:-1],
        }


# ──────────────────────────────────────────────
# NEW: Transformer-based predictor
# ──────────────────────────────────────────────
class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 512, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))

        pe[:, 0::2] = torch.sin(position * div_term)
        if d_model % 2 == 0:
            pe[:, 1::2] = torch.cos(position * div_term)
        else:
            pe[:, 1::2] = torch.cos(position * div_term[: d_model // 2])

        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, : x.size(1)]
        return self.dropout(x)


class MinesTransformerModel(nn.Module):
    def __init__(
        self,
        grid_size: int = 25,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 3,
        dim_feedforward: int = 128,
        dropout: float = 0.1,
        seq_len: int = 10,
    ):
        super().__init__()
        self.grid_size = grid_size
        self.seq_len = seq_len
        self.d_model = d_model

        # Each game round is a binary vector of grid_size -> project to d_model
        self.input_proj = nn.Linear(grid_size, d_model)
        self.pos_enc = PositionalEncoding(d_model, max_len=seq_len, dropout=dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        self.output_head = nn.Sequential(
            nn.Linear(d_model, dim_feedforward),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(dim_feedforward, grid_size),
            nn.Sigmoid(),  # probability per cell of being a mine
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (batch, seq_len, grid_size) — binary vectors of past mine positions
        returns: (batch, grid_size) — probability of each cell being a mine next round
        """
        x = self.input_proj(x)          # (batch, seq_len, d_model)
        x = self.pos_enc(x)             # (batch, seq_len, d_model)
        x = self.transformer(x)         # (batch, seq_len, d_model)
        x = x[:, -1, :]                 # take last token: (batch, d_model)
        return self.output_head(x)      # (batch, grid_size)


class MinesTransformer:
    """High-level wrapper used by Flask routes."""

    def __init__(
        self,
        grid_size: int = 25,
        seq_len: int = 10,
        weights_path: str = "weights.pt",
        device: str | None = None,
    ):
        self.grid_size = grid_size
        self.seq_len = seq_len
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.model = MinesTransformerModel(grid_size=grid_size, seq_len=seq_len)

        try:
            state = torch.load(weights_path, map_location=self.device, weights_only=True)
            self.model.load_state_dict(state)
            self.ready = True
            print(f"[MinesTransformer] Weights loaded from {weights_path}")
        except FileNotFoundError:
            self.ready = False
            print(f"[MinesTransformer] No weights at {weights_path} — model uninitialized")

        self.model.to(self.device)
        self.model.eval()

    def _history_to_tensor(self, history: list[list[int]]) -> torch.Tensor:
        """Convert list of mine-position lists into (1, seq_len, grid_size) tensor."""
        frames = []
        for mines in history[-self.seq_len :]:
            vec = [0.0] * self.grid_size
            for pos in mines:
                idx = pos - 1  # positions are 1-indexed
                if 0 <= idx < self.grid_size:
                    vec[idx] = 1.0
            frames.append(vec)

        # Pad front if not enough history
        while len(frames) < self.seq_len:
            frames.insert(0, [0.0] * self.grid_size)

        arr = np.array(frames, dtype=np.float32)
        return torch.tensor(arr, device=self.device).unsqueeze(0)  # (1, seq_len, grid_size)

    @torch.no_grad()
    def predict_safe(self, history: list[list[int]], num_safe: int = 5) -> dict:
        if not self.ready:
            return {
                "safe_cells": [],
                "confidence": 0.0,
                "error": "Model weights not loaded. Train first.",
            }

        x = self._history_to_tensor(history)
        probs = self.model(x).squeeze(0).cpu().numpy()  # (grid_size,)

        # Cells with lowest mine probability = safest
        indices = np.argsort(probs)
        safe_cells = sorted([int(i) + 1 for i in indices[:num_safe]])

        avg_mine_prob = float(np.mean(probs[indices[:num_safe]]))
        confidence = round((1.0 - avg_mine_prob) * 100, 2)

        return {
            "safe_cells": safe_cells,
            "confidence": confidence,
            "mine_probabilities": {int(i) + 1: round(float(p), 4) for i, p in enumerate(probs)},
        }
