#!/usr/bin/env python3
"""
Train the MinesTransformer on historical game data from MongoDB.

Usage:
    python train.py                         # defaults
    python train.py --epochs 200 --lr 0.0005 --seq-len 15
"""
import os
import argparse
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from pymongo import MongoClient

from model import MinesTransformerModel


# ──────────────────────────────────────────────
# Dataset
# ──────────────────────────────────────────────
class MinesDataset(Dataset):
    def __init__(self, games: list[list[int]], grid_size: int = 25, seq_len: int = 10):
        self.grid_size = grid_size
        self.seq_len = seq_len
        self.samples = []

        # Build sliding-window samples: (seq_len rounds of input) -> (next round as label)
        for i in range(len(games) - seq_len):
            window = games[i : i + seq_len]
            target = games[i + seq_len]
            self.samples.append((window, target))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        window, target = self.samples[idx]

        # Convert to binary grids
        x = np.zeros((self.seq_len, self.grid_size), dtype=np.float32)
        for t, mines in enumerate(window):
            for pos in mines:
                ci = pos - 1
                if 0 <= ci < self.grid_size:
                    x[t, ci] = 1.0

        y = np.zeros(self.grid_size, dtype=np.float32)
        for pos in target:
            ci = pos - 1
            if 0 <= ci < self.grid_size:
                y[ci] = 1.0

        return torch.tensor(x), torch.tensor(y)


# ──────────────────────────────────────────────
# Training loop
# ──────────────────────────────────────────────
def train(args):
    # Connect to MongoDB
    mongo_uri = os.getenv(
        "MONGO_URI",
        "mongodb+srv://jackson:mines2024@cluster0.mongodb.net/mines_bot?retryWrites=true&w=majority",
    )
    client = MongoClient(mongo_uri)
    col = client["mines_bot"]["games"]

    docs = list(col.find().sort("timestamp", 1))
    games = [doc["mines_positions"] for doc in docs if "mines_positions" in doc]

    print(f"[train] Loaded {len(games)} games from MongoDB")

    if len(games) < args.seq_len + 10:
        print(f"[train] Need at least {args.seq_len + 10} games to train. Record more via /result.")
        return

    # Split 90/10
    split = int(len(games) * 0.9)
    train_ds = MinesDataset(games[:split], grid_size=args.grid_size, seq_len=args.seq_len)
    val_ds = MinesDataset(games[split:], grid_size=args.grid_size, seq_len=args.seq_len)

    print(f"[train] Train samples: {len(train_ds)} | Val samples: {len(val_ds)}")

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[train] Device: {device}")

    model = MinesTransformerModel(
        grid_size=args.grid_size,
        d_model=args.d_model,
        nhead=args.nhead,
        num_layers=args.num_layers,
        dim_feedforward=args.dim_ff,
        seq_len=args.seq_len,
    ).to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    criterion = nn.BCELoss()

    best_val_loss = float("inf")

    for epoch in range(1, args.epochs + 1):
        # ---- Train ----
        model.train()
        train_loss = 0.0
        for x_batch, y_batch in train_loader:
            x_batch, y_batch = x_batch.to(device), y_batch.to(device)
            preds = model(x_batch)
            loss = criterion(preds, y_batch)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item()

        train_loss /= max(len(train_loader), 1)

        # ---- Validate ----
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for x_batch, y_batch in val_loader:
                x_batch, y_batch = x_batch.to(device), y_batch.to(device)
                preds = model(x_batch)
                val_loss += criterion(preds, y_batch).item()

        val_loss /= max(len(val_loader), 1)
        scheduler.step()

        if epoch % 10 == 0 or epoch == 1:
            lr_now = scheduler.get_last_lr()[0]
            print(f"  Epoch {epoch:>4d}/{args.epochs} | train_loss={train_loss:.5f} | val_loss={val_loss:.5f} | lr={lr_now:.6f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), args.output)
            if epoch % 10 == 0:
                print(f"  -> Saved best weights to {args.output}")

    print(f"\n[train] Done. Best val_loss={best_val_loss:.5f} | Weights at {args.output}")


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Train MinesTransformer")
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr", type=float, default=0.001)
    p.add_argument("--seq-len", type=int, default=10)
    p.add_argument("--grid-size", type=int, default=25)
    p.add_argument("--d-model", type=int, default=64)
    p.add_argument("--nhead", type=int, default=4)
    p.add_argument("--num-layers", type=int, default=3)
    p.add_argument("--dim-ff", type=int, default=128)
    p.add_argument("--output", type=str, default="weights.pt")
    train(p.parse_args())
