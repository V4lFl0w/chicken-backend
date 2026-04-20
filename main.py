import asyncio
import random
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# import socketio  # TODO: pip install python-socketio — нужен для мультиплеера
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text  # Нужно для выполнения сырого SQL
from database import SessionLocal, Player, QuizQuestion, engine, Base
from quiz_manager import background_fill_bank, get_random_questions, MIN_QUESTIONS

WHEEL_PRIZES = [
    {"id": 0, "type": "cc", "amount": 100},
    {"id": 1, "type": "cc", "amount": 500},
    {"id": 2, "type": "cc", "amount": 1000},
    {"id": 3, "type": "gf", "amount": 2},
    {"id": 4, "type": "gf", "amount": 5},
    {"id": 5, "type": "gf", "amount": 10},
]
WHEEL_WEIGHTS = [35, 30, 15, 12, 6, 2]

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
async def on_startup():
    with engine.begin() as conn:
        try:
            # Пытаемся добавить колонку nickname (ошибку игнорируем, если уже есть)
            conn.execute(text("ALTER TABLE game_players ADD COLUMN nickname VARCHAR;"))
        except:
            pass
        try:
            conn.execute(text("ALTER TABLE game_players ADD COLUMN coins INTEGER DEFAULT 0;"))
        except:
            pass
        try:
            conn.execute(text("ALTER TABLE game_players ADD COLUMN IF NOT EXISTS chicken_coins INTEGER DEFAULT 0;"))
        except:
            pass
        try:
            conn.execute(text("ALTER TABLE game_players ADD COLUMN IF NOT EXISTS golden_feathers INTEGER DEFAULT 0;"))
        except:
            pass
        try:
            conn.execute(text("ALTER TABLE game_players ADD COLUMN IF NOT EXISTS inventory JSON DEFAULT '[]';"))
        except:
            pass
        try:
            conn.execute(text("ALTER TABLE game_players ADD COLUMN IF NOT EXISTS last_spin_date TIMESTAMP;"))
        except:
            pass
        try:
            conn.execute(text("ALTER TABLE game_players ADD COLUMN IF NOT EXISTS wins INTEGER DEFAULT 0;"))
        except:
            pass
        try:
            conn.execute(text("UPDATE game_players SET chicken_coins = coins WHERE chicken_coins = 0 AND coins > 0;"))
        except:
            pass

    # ЗАПУСКАЕМ ФОНОВУЮ ГЕНЕРАЦИЮ ВОПРОСОВ ПРИ СТАРТЕ СЕРВЕРА
    asyncio.create_task(background_fill_bank())

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

class SpinData(BaseModel):
    telegram_id: int

class StatsData(BaseModel):
    telegram_id: int
    stat_type: str  # "win" supported

@app.post("/get_user")
def get_user(data: UserData, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.telegram_id == data.telegram_id).first()
    if not player:
        player = Player(telegram_id=data.telegram_id, username=data.username, nickname=data.username)
        db.add(player)
        db.commit()
        db.refresh(player)
    
    display_name = (player.nickname.strip() if player.nickname and player.nickname.strip() else None) or player.username or "Игрок"
    now = datetime.utcnow()
    can_spin = True
    cooldown_seconds = 0
    if player.last_spin_date:
        elapsed = (now - player.last_spin_date).total_seconds()
        if elapsed < 86400:
            can_spin = False
            cooldown_seconds = int(86400 - elapsed)
    return {
        "telegram_id":      player.telegram_id,
        "nickname":         display_name,
        "high_score":       player.high_score,
        "coins":            player.coins,
        "chicken_coins":    player.chicken_coins    if player.chicken_coins    is not None else 0,
        "golden_feathers":  player.golden_feathers  if player.golden_feathers  is not None else 0,
        "inventory":        player.inventory         if player.inventory         is not None else [],
        "wins":             player.wins              if player.wins              is not None else 0,
        "can_spin":         can_spin,
        "cooldown_seconds": cooldown_seconds,
    }

@app.post("/save_score")
def save_score(data: ScoreData, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.telegram_id == data.telegram_id).first()
    if not player:
        player = Player(telegram_id=data.telegram_id, username=data.username, nickname=data.username)
        db.add(player)
    else:
        player.nickname = data.username
    
    if data.score > player.high_score:
        player.high_score = data.score
        
    player.coins += data.coins  # Сохраняем монеты в банк
    db.commit()
    
    return {"message": "Успех", "coins_total": player.coins, "high_score": player.high_score}

@app.get("/top_players")
def get_top_players(limit: int = 10, db: Session = Depends(get_db)):
    players = db.query(Player).order_by(Player.high_score.desc()).limit(limit).all()
    
    top_list = []
    for p in players:
        display_name = p.nickname if p.nickname else "Аноним"
        top_list.append({"nickname": display_name, "score": p.high_score})
        
    return top_list

# --- ОДНОРАЗОВАЯ МИГРАЦИЯ (дернуть один раз руками) ---
@app.get("/force_migrate")
def force_migrate(db: Session = Depends(get_db)):
    with engine.begin() as conn:
        conn.execute(text("UPDATE game_players SET chicken_coins = coins;"))
    return {"status": "ok", "message": "chicken_coins = coins для всех игроков"}

# --- СТАТИСТИКА ---
@app.post("/update_stats")
def update_stats(data: StatsData, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.telegram_id == data.telegram_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Игрок не найден")
    if data.stat_type == "win":
        player.wins = (player.wins or 0) + 1
    else:
        raise HTTPException(status_code=400, detail=f"Неизвестный stat_type: {data.stat_type}")
    db.commit()
    return {"wins": player.wins}

# --- КОЛЕСО ФОРТУНЫ ---
@app.post("/spin_wheel")
def spin_wheel(data: SpinData, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.telegram_id == data.telegram_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Игрок не найден")

    now = datetime.utcnow()
    if player.last_spin_date:
        elapsed = (now - player.last_spin_date).total_seconds()
        if elapsed < 86400:
            raise HTTPException(status_code=429, detail="cooldown", headers={
                "X-Cooldown-Seconds": str(int(86400 - elapsed))
            })

    prize = random.choices(WHEEL_PRIZES, weights=WHEEL_WEIGHTS, k=1)[0]
    if prize["type"] == "cc":
        player.chicken_coins = (player.chicken_coins or 0) + prize["amount"]
    else:
        player.golden_feathers = (player.golden_feathers or 0) + prize["amount"]
    player.last_spin_date = now
    db.commit()

    return {
        "prize_id":       prize["id"],
        "prize_type":     prize["type"],
        "prize_amount":   prize["amount"],
        "chicken_coins":  player.chicken_coins,
        "golden_feathers":player.golden_feathers,
    }

# --- ЭНДПОИНТ ДЛЯ ВИКТОРИНЫ ---
@app.get("/get_quiz_questions")
def api_get_quiz_questions(db: Session = Depends(get_db)):
    # Проверяем, не иссякли ли запасы
    count = db.query(QuizQuestion).count()
    if count < MIN_QUESTIONS:
        # Если вопросов мало - пинаем генератор
        asyncio.create_task(background_fill_bank())
        
    # Достаем 12 случайных вопросов и отдаем игре
    questions = get_random_questions(limit=12)
    return questions