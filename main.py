from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import database # Импортируем наш новый файл базы данных

app = FastAPI()

# Разрешаем нашему WebApp отправлять запросы
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модель данных, которую присылает игра
class ScoreData(BaseModel):
    telegram_id: int
    username: str
    score: int

# Функция для получения сессии базы данных
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"status": "Бэкенд игры успешно запущен! 🚀"}

@app.post("/save_score")
def save_score(data: ScoreData, db: Session = Depends(get_db)):
    # Ищем игрока в базе по его telegram_id
    player = db.query(database.Player).filter(database.Player.telegram_id == data.telegram_id).first()

    if not player:
        # Если такого игрока еще нет — создаем нового
        player = database.Player(telegram_id=data.telegram_id, username=data.username, high_score=data.score)
        db.add(player)
        message = "Новый игрок зарегистрирован в базе!"
    else:
        # Если игрок есть, проверяем, побил ли он свой старый рекорд
        if data.score > player.high_score:
            player.high_score = data.score
            message = "Новый рекорд установлен!"
        else:
            message = f"Очки получены, но рекорд ({player.high_score}) не побит."

    # Сохраняем изменения
    db.commit()
    return {"message": message, "high_score": player.high_score}