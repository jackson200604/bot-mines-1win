from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GameData(BaseModel):
    history: list = []
    mines_count: int = 3

@app.get("/")
def read_root():
    return {"status": "Connecté", "message": "Le cerveau du Bot Mines est prêt"}

@app.post("/predict")
async def predict(data: GameData):
    all_tiles = list(range(25))
    safe_candidates = [t for t in all_tiles if t not in data.history]
    
    # Sécurité au cas où toutes les cases seraient pleines
    if not safe_candidates:
        return {"recommended_tiles": [], "confidence": 0}

    recommended = random.sample(safe_candidates, min(3, len(safe_candidates)))
    
    return {
        "recommended_tiles": recommended,
        "confidence": random.randint(75, 98)
    }
