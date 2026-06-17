from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import urllib.request
from . import crud, schemas, models
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="UniAgent System API")

# DB Bağlantı Dependency-si
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/universities/", response_model=schemas.University)
def create_university(university: schemas.UniversityCreate, db: Session = Depends(get_db)):
    return crud.create_university(db=db, university=university)

@app.get("/universities/", response_model=List[schemas.University])
def read_universities(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_universities(db, skip=skip, limit=limit)

@app.post("/programs/", response_model=schemas.Program)
def create_program(program: schemas.ProgramCreate, db: Session = Depends(get_db)):
    return crud.create_program(db=db, program=program)

# 🔥 YENİ: Universitet Saytını Avtomatik Skrap Edən Endpoint
@app.post("/universities/{university_id}/scrape/")
def scrape_university_website(university_id: int, db: Session = Depends(get_db)):
    # 1. Universitetin bazada olub-olmadığını yoxla
    db_uni = db.query(models.University).filter(models.University.id == university_id).first()
    if not db_uni:
        raise HTTPException(status_code=404, detail="Universitet tapılmadı!")
    
    if not db_uni.website_url:
        raise HTTPException(status_code=400, detail="Bu universitetin veb-sayt linki yoxdur!")

    try:
        # 2. Sayta sorğu göndər (Bloklanmamaq üçün User-Agent əlavə edirik)
        req = urllib.request.Request(
            db_uni.website_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        
        # 3. HTML məzmununu yüklə
        with urllib.request.urlopen(req, timeout=15) as response:
            html_content = response.read().decode('utf-8', errors='ignore')
        
        # 4. Xam HTML-i skrap olunmuş səhifələr (scraped_pages) cədvəlinə yaz
        scraped_page = crud.save_scraped_page(
            db=db, 
            university_id=university_id, 
            url=db_uni.website_url, 
            html_content=html_content
        )
        
        return {
            "status": "Uğurlu!",
            "message": f"{db_uni.name} saytı uğurla skrap olundu və bazaya qeyd edildi.",
            "scraped_page_id": scraped_page.id,
            "html_length": len(html_content)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skrap zamanı xəta baş verdi: {str(e)}")