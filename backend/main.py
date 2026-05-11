from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random

app = FastAPI()

# LE VIGILE (CORS) : C'est ici que la magie opère
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
    # Logique temporaire avant d'avoir assez de données pour le ML
    all_tiles = list(range(25))
    safe_candidates = [t for t in all_tiles if t not in data.history]
    
    # On choisit 3 cases au hasard parmi celles qui n'ont pas encore explosé
    recommended = random.sample(safe_candidates, min(3, len(safe_candidates)))
    
    return {
        "recommended_tiles": recommended,
        "confidence": random.randint(70, 95)
    }        "confidence": random.randint(75, 98) # Indice de confiance fictif
    }
