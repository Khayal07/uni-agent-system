from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import urllib.request
import json
import os
import re  # HTML-i tamamilə təmizləmək üçün standart kitabxana
import requests
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


# 5. 🔥 YENİLƏNMİŞ ADDIM: TƏMİZ MƏTNİ SƏNİN MODELİNLƏ EMAL EDİB BAZAYA YAZMAQ
@app.post("/universities/{university_id}/process-with-ai/")
def process_html_with_openrouter(university_id: int, db: Session = Depends(get_db)):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or api_key.strip() == "":
        raise HTTPException(status_code=400, detail="OPENROUTER_API_KEY tapılmadı! .env faylını yoxlayın.")

    scraped_data = db.query(models.ScrapedPage).filter(models.ScrapedPage.university_id == university_id).order_by(models.ScrapedPage.scraped_at.desc()).first()
    if not scraped_data:
        raise HTTPException(status_code=404, detail="Bu universitet üçün skrap olunmuş xam HTML tapılmadı. Öncə scrape endpointini işə salın!")

    # 🪓 ULTRA-TƏMİZLƏMƏ FİLTRİ: HTML kodlarını tamamilə qırxırıq
    raw_html = scraped_data.raw_html
    
    # 1. <head>...</head> hissəsini və daxilindəki bütün lazımsız linkləri tamamilə silirik
    cleaned_text = re.sub(r'<head\b[^>]*>.*?</head>', '', raw_html, flags=re.DOTALL | re.IGNORECASE)
    # 2. Ssenari və stil bloklarını silirik
    cleaned_text = re.sub(r'<script\b[^>]*>.*?</script>', '', cleaned_text, flags=re.DOTALL | re.IGNORECASE)
    cleaned_text = re.sub(r'<style\b[^>]*>.*?</style>', '', cleaned_text, flags=re.DOTALL | re.IGNORECASE)
    # 3. GERİDƏ QALAN BÜTÜN HTML TEQLƏRİNİ SİLİRİK (Yalnız təmiz görünən yazılar qalır)
    cleaned_text = re.sub(r'<[^>]+>', ' ', cleaned_text)
    # 4. Artıq boşluqları sıxırıq
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    # Model üçün tapşırıq (Prompt) - İndi model qarşısında təmiz mətn görəcək
    prompt = f"""
    You are an expert AI Data Engineer. Analyze the following clean text extracted from a university website and extract all academic programs (bachelor, master, or phd majors).
    
    Strictly return a valid JSON array of objects, where each object has exactly these keys:
    - "faculty": Name of the faculty or department.
    - "program_name": Name of the major/study program.
    - "degree": Degree level (e.g., Bachelor, Master, PhD).
    - "language": Language of instruction (e.g., Azerbaijani, English, Russian).
    - "tuition_fee": Tuition fee if mentioned, otherwise null.
    - "requirements": Any specific entry requirements mentioned, otherwise null.

    Do not include any markdown formatting like ```json ... ``` or thinking tags. Return raw JSON text only. If no programs are found, return an empty array [].
    
    Website Clean Text Content:
    {cleaned_text[:40000]}
    """

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openai/gpt-oss-120b:free",  # 🔥 Sənin canavar kimi işləyən pulsuz modelin
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 3000
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=45)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"OpenRouter API xəta qaytardı: {response.text}"
            )
            
        result = response.json()
        ai_response_text = result['choices'][0]['message']['content'].strip()

        # Model nəsə əlavə teq qoyubsa təmizləyirik
        if "</think>" in ai_response_text:
            ai_response_text = ai_response_text.split("</think>")[-1].strip()
            
        if ai_response_text.startswith("```"):
            first_newline = ai_response_text.find("\n")
            last_backticks = ai_response_text.rfind("```")
            if first_newline != -1 and last_backticks != -1:
                ai_response_text = ai_response_text[first_newline:last_backticks].strip()

        extracted_programs = json.loads(ai_response_text)

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
            "message": f"AI mətni təmizlədi. {saved_count} yeni ixtisas bazaya yazıldı!",
            "programs_extracted": extracted_programs,
            "AI_MODELIN_QAYTARDIGI_XAM_METN": ai_response_text,
            "BAZADAN_AI_A_GEDEN_MƏTN_SNIPPET": cleaned_text[:1000]
        }

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail=f"AI-dan düzgün JSON strukturu qayıtmadı. Modelin qaytardığı mətn: {ai_response_text}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Emalı zamanı xəta: {str(e)}")