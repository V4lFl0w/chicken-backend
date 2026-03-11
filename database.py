import os
from sqlalchemy import create_engine, Column, Integer, BigInteger, String, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL не найдена в переменных окружения!")
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Player(Base):
    __tablename__ = "game_players"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    username = Column(String, nullable=True)
    nickname = Column(String, nullable=True) # Задел для выбора своего имени
    high_score = Column(Integer, default=0)
    coins = Column(Integer, default=0)       # Банк игрока

# --- НОВАЯ ТАБЛИЦА ДЛЯ ВОПРОСОВ ---
class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    id = Column(Integer, primary_key=True, index=True)
    q = Column(String, nullable=False)       # Сам вопрос
    a = Column(JSON, nullable=False)         # Массив вариантов ответов ["А", "Б", "В", "Г"]
    c = Column(Integer, nullable=False)      # Индекс правильного ответа (0, 1, 2, 3)

Base.metadata.create_all(bind=engine)