from sqlalchemy import create_engine, Column, Integer, BigInteger, String
from sqlalchemy.orm import declarative_base, sessionmaker

# СЮДА ВСТАВЬ СВОЮ ССЫЛКУ НА БАЗУ ДАННЫХ ОТ DIARY BOT
# Важно: если в ссылке есть "+asyncpg", убери его!
# Пример правильной ссылки: "postgresql://user:password@host:port/dbname"
DATABASE_URL = "postgresql://doadmin:AVNS_TaXlCDUTUTvVzp7Bpd3@db-postgresql-fra1-86053-do-user-31907194-0.k.db.ondigitalocean.com:25060/defaultdb"

# Подключаемся к базе
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Описываем таблицу для хранения очков
class Player(Base):
    __tablename__ = "game_players" # Название таблицы в базе

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True) # ID юзера в Телеге
    username = Column(String, nullable=True) # Никнейм
    high_score = Column(Integer, default=0) # Лучший счет

# Эта команда автоматически создаст таблицу "game_players" в твоей базе, если её там еще нет
Base.metadata.create_all(bind=engine)