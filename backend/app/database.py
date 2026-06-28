from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Mərkəzləşmiş konfiqurasiyadan baza URL-ni alırıq (.env load_dotenv ilə oxunur)
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Bazaya qoşulub işi bitəndə avtomatik bağlayan asılılıq (Dependency)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()