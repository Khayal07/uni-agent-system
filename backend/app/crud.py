from sqlalchemy.orm import Session
from . import models, schemas

# Universitet əlavə etmək
def create_university(db: Session, university: schemas.UniversityCreate):
    db_uni = models.University(name=university.name, website_url=university.website_url)
    db.add(db_uni)
    db.commit()
    db.refresh(db_uni)
    return db_uni

# Universitetləri siyahılamaq
def get_universities(db: Session, skip: int = 0, limit: int = 10):
    return db.query(models.University).offset(skip).limit(limit).all()

# Proqram (İxtisas) əlavə etmək
def create_program(db: Session, program: schemas.ProgramCreate):
    db_program = models.Program(**program.model_dump())
    db.add(db_program)
    db.commit()
    db.refresh(db_program)
    return db_program

# Xam HTML səhifəni bazaya yadda saxlamaq (Scraper üçün)
def save_scraped_page(db: Session, university_id: int, url: str, html_content: str):
    db_page = models.ScrapedPage(
        university_id=university_id,
        url=url,
        raw_html=html_content
    )
    db.add(db_page)
    db.commit()
    db.refresh(db_page)
    return db_page