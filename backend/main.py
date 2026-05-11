from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from model import MinesPredictor

app = FastAPI()
predictor = MinesPredictor()

class GameData(BaseModel):
    history: list
    mines_count: int

@app.get("/")
def home():
    return {"status": "Bot Mines API Online"}

@app.post("/predict")
async def predict(data: GameData):
    # Logique pour appeler ton ML
    prediction = predictor.get_safe_tiles(data.history, data.mines_count)
    return {"recommended_tiles": prediction}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
