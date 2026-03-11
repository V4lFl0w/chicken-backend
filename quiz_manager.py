import json
import asyncio
import os
from sqlalchemy.sql.expression import func
from database import SessionLocal, QuizQuestion

# Сюда вставь свой ключ OpenAI (или пропиши его в ENV на сервере)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "ТВОЙ_КЛЮЧ_СЮДА")

# Настройки буфера
MIN_QUESTIONS = 100   # При каком остатке начинать экстренную генерацию
TARGET_BANK = 1000    # Сколько вопросов держать в базе
BATCH_SIZE = 15       # По сколько штук генерировать за 1 раз

is_generating = False

async def generate_batch():
    prompt = f"""
    Сгенерируй {BATCH_SIZE} уникальных и интересных вопросов для викторины (наука, история, кино, игры, технологии, география).
    Отвечай СТРОГО массивом JSON без форматирования Markdown (без ```json).
    Формат:
    [
      {{ "q": "Текст вопроса?", "a": ["Вариант1", "Вариант2", "Вариант3", "Вариант4"], "c": 0 }}
    ]
    Индекс правильного ответа (c) должен быть от 0 до 3.
    """
    
    def fetch_from_openai():
        try:
            # Для новой версии библиотеки openai (v1.0+)
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini", # Дешевая и умная модель
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8
            )
            return response.choices[0].message.content
        except ImportError:
            # Фоллбек, если стоит старая версия openai
            import openai
            openai.api_key = OPENAI_API_KEY
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8
            )
            return response.choices[0].message.content

    try:
        # Вызываем синхронный запрос в отдельном потоке, чтобы не блочить сервер
        raw_json = await asyncio.to_thread(fetch_from_openai)
        
        # Очистка, если нейронка все-таки прислала markdown
        raw_json = raw_json.strip()
        if raw_json.startswith("```json"):
            raw_json = raw_json[7:-3]
        elif raw_json.startswith("```"):
            raw_json = raw_json[3:-3]
            
        questions = json.loads(raw_json)
        return questions
    except Exception as e:
        print(f"[QuizManager] Ошибка генерации: {e}")
        return []

async def background_fill_bank():
    """Фоновый процесс наполнения базы"""
    global is_generating
    if is_generating: return
    is_generating = True
    
    db = SessionLocal()
    try:
        current_count = db.query(QuizQuestion).count()
        
        while current_count < TARGET_BANK:
            print(f"[QuizManager] Пополнение... База: {current_count}/{TARGET_BANK}")
            new_questions = await generate_batch()
            
            if new_questions:
                added = 0
                for q in new_questions:
                    if "q" in q and "a" in q and "c" in q:
                        db_q = QuizQuestion(q=q["q"], a=q["a"], c=q["c"])
                        db.add(db_q)
                        added += 1
                db.commit()
                current_count = db.query(QuizQuestion).count()
                print(f"[QuizManager] Добавлено {added} вопросов.")
            
            # Пауза, чтобы не дудосить OpenAI и не словить бан
            await asyncio.sleep(5) 
            
    except Exception as e:
        print(f"[QuizManager] Ошибка процесса: {e}")
    finally:
        db.close()
        is_generating = False

def get_random_questions(limit=12):
    """Вытаскивает рандомные вопросы для игры"""
    db = SessionLocal()
    try:
        # Берем случайные строки из таблицы (func.random работает и в SQLite, и в Postgres)
        questions = db.query(QuizQuestion).order_by(func.random()).limit(limit).all()
        
        # Опционально: можно удалять их, чтобы база реально обновлялась
        # db.query(QuizQuestion).filter(QuizQuestion.id.in_([q.id for q in questions])).delete(synchronize_session=False)
        # db.commit()
        
        return [{"q": q.q, "a": q.a, "c": q.c} for q in questions]
    finally:
        db.close()