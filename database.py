import os
from sqlalchemy import create_engine, Column, Integer, BigInteger, String
from sqlalchemy.orm import declarative_base, sessionmaker

# Теперь мы берем ссылку из переменной окружения
# Если ее нет в системе, будет ошибка, что безопасно
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL не найдена в переменных окружения!")

# Если в ссылке есть asyncpg, меняем на синхронный драйвер
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
    high_score = Column(Integer, default=0)

Base.metadata.create_all(bind=engine)