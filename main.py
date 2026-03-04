from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text  # Нужно для выполнения сырого SQL
from database import SessionLocal, Player, engine, Base

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# АВТО-ОБНОВЛЕНИЕ БАЗЫ ДАННЫХ
@app.on_event("startup")
def on_startup():
    with engine.begin() as conn:
        try:
            # Пытаемся добавить колонку nickname (ошибку игнорируем, если уже есть)
            conn.execute(text("ALTER TABLE game_players ADD COLUMN nickname VARCHAR;"))
        except:
            pass
        try:
            # Пытаемся добавить колонку coins
            conn.execute(text("ALTER TABLE game_players ADD COLUMN coins INTEGER DEFAULT 0;"))
        except:
            pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ScoreData(BaseModel):
    telegram_id: int
    username: str
    score: int
    coins: int = 0  # Принимаем монеты

class UserData(BaseModel):
    telegram_id: int
    username: str

@app.post("/get_user")
def get_user(data: UserData, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.telegram_id == data.telegram_id).first()
    if not player:
        player = Player(telegram_id=data.telegram_id, username=data.username, nickname=data.username)
        db.add(player)
        db.commit()
        db.refresh(player)
    
    return {
        "telegram_id": player.telegram_id,
        "nickname": player.nickname,
        "high_score": player.high_score,
        "coins": player.coins
    }

@app.post("/save_score")
def save_score(data: ScoreData, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.telegram_id == data.telegram_id).first()
    if not player:
        player = Player(telegram_id=data.telegram_id, username=data.username, nickname=data.username)
        db.add(player)
    
    if data.score > player.high_score:
        player.high_score = data.score
        
    player.coins += data.coins  # Сохраняем монеты в банк
    db.commit()
    
    return {"message": "Успех", "coins_total": player.coins, "high_score": player.high_score}