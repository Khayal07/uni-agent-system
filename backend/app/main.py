from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import urllib.request
import json
import os
from . import crud, schemas, models
from .database import SessionLocal, engine

# Baza cədvəllərini yaradırıq
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="UniAgent System API")

# DB Bağlantı Dependency-si
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. Universitet Əlavə Etmək
@app.post("/universities/", response_model=schemas.University)
def create_university(university: schemas.UniversityCreate, db: Session = Depends(get_db)):
    return crud.create_university(db=db, university=university)

# 2. Universitetləri Siyahılamaq
@app.get("/universities/", response_model=List[schemas.University])
def read_universities(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_universities(db, skip=skip, limit=limit)

# 3. İxtisas (Proqram) Əlavə Etmək
@app.post("/programs/", response_model=schemas.Program)
def create_program(program: schemas.ProgramCreate, db: Session = Depends(get_db)):
    return crud.create_program(db=db, program=program)

# 4. Saytı Skrap Edib Xam HTML-i Bazaya Atmaq
@app.post("/universities/{university_id}/scrape/")
def scrape_university_website(university_id: int, db: Session = Depends(get_db)):
    db_uni = db.query(models.University).filter(models.University.id == university_id).first()
    if not db_uni:
        raise HTTPException(status_code=404, detail="Universitet tapılmadı!")
    if not db_uni.website_url:
        raise HTTPException(status_code=400, detail="Bu universitetin veb-sayt linki yoxdur!")

    try:
        req = urllib.request.Request(
            db_uni.website_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            html_content = response.read().decode('utf-8', errors='ignore')
        
        scraped_page = crud.save_scraped_page(db=db, university_id=university_id, url=db_uni.website_url, html_content=html_content)
        return {"status": "Uğurlu!", "scraped_page_id": scraped_page.id, "html_length": len(html_content)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skrap xətası: {str(e)}")


# 5. 🔥 YENİ ADDIM: HTML-İ GEMINI AI ILƏ EMAL EDİB İXTİSASLARI BAZAYA YAZMAQ
@app.post("/universities/{university_id}/process-with-ai/")
def process_html_with_gemini(university_id: int, db: Session = Depends(get_db)):
    # .env faylından Gemini API Key-i oxuyuruq
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY tapılmadı! .env faylını yoxlayın.")

    # Bazadan bu universitetə aid ən son skrap olunmuş xam HTML-i tapırıq
    scraped_data = db.query(models.ScrapedPage).filter(models.ScrapedPage.university_id == university_id).order_by(models.ScrapedPage.scraped_at.desc()).first()
    if not scraped_data:
        raise HTTPException(status_code=404, detail="Bu universitet üçün skrap olunmuş xam HTML tapılmadı. Öncə scrape endpointini işə salın!")

    # Gemini-yə tapşırıq (Prompt) veririk
    prompt = f"""
    You are an expert AI Data Engineer. Analyze the following raw HTML from a university website and extract all academic programs (bachelor, master, or phd majors).
    
    Strictly return a valid JSON array of objects, where each object has exactly these keys:
    - "faculty": Name of the faculty or department.
    - "program_name": Name of the major/study program.
    - "degree": Degree level (e.g., Bachelor, Master, PhD).
    - "language": Language of instruction (e.g., Azerbaijani, English, Russian).
    - "tuition_fee": Tuition fee if mentioned, otherwise null.
    - "requirements": Any specific entry requirements mentioned, otherwise null.

    Do not include any markdown formatting like ```json ... ```. Return raw JSON text only.
    
    HTML Content:
    {scraped_data.raw_html[:40000]}
    """

    # Gemini API-yə birbaşa sorğu göndərilməsi
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        ai_response_text = result['candidates'][0]['content']['parts'][0]['text']
        extracted_programs = json.loads(ai_response_text)

        # Gemini-dən gələn təmiz datanı 'programs' cədvəlinə doldururuq
        saved_count = 0
        for prog in extracted_programs:
            program_schema = schemas.ProgramCreate(
                university_id=university_id,
                faculty=prog.get("faculty", "Unknown"),
                program_name=prog.get("program_name", "Unknown"),
                degree=prog.get("degree", "Bachelor"),
                language=prog.get("language", "Azerbaijani"),
                tuition_fee=str(prog.get("tuition_fee")) if prog.get("tuition_fee") else None,
                requirements=prog.get("requirements")
            )
            crud.create_program(db=db, program=program_schema)
            saved_count += 1

        return {
            "status": "Uğurlu!",
            "message": f"Gemini HTML-i təmizlədi. {saved_count} yeni ixtisas bazaya yazıldı!",
            "programs_extracted": extracted_programs
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Emalı zamanı xəta: {str(e)}")