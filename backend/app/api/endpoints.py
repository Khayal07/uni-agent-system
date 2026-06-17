import os
import google.generativeai as genai
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, schemas
from app.database import get_db

router = APIRouter()

@router.post("/universities/", response_model=schemas.University)
def create_university(university: schemas.UniversityCreate, db: Session = Depends(get_db)):
    return crud.create_university(db=db, university=university)

@router.get("/universities/", response_model=list[schemas.University])
def read_universities(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_universities(db=db, skip=skip, limit=limit)

@router.post("/universities/{university_id}/scrape/")
def scrape_university_website(university_id: int, db: Session = Depends(get_db)):
    db_university = crud.get_university(db, university_id=university_id)
    if not db_university:
        raise HTTPException(status_code=404, detail="Universitet tapılmadı!")
    return {"status": "success", "message": "Xam HTML uğurla skrap olundu!"}

# 🔥 BAX MODELİ VƏ GEMINI-Nİ BURADA TƏYİN EDİRİK!
@router.post("/universities/{university_id}/process-with-ai/")
def process_html_with_gemini(university_id: int, db: Session = Depends(get_db)):
    
    # 1. .env faylından API açarını oxuyuruq
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() == "" or api_key == "bura_yaz":
        raise HTTPException(
            status_code=400, 
            detail="Zəhmət olmasa .env faylında real GEMINI_API_KEY təyin edin!"
        )
    
    # 2. Bazadan universiteti və onun skrap olunmuş HTML-ini çəkirik
    db_university = crud.get_university(db, university_id=university_id)
    if not db_university:
        raise HTTPException(status_code=404, detail="Universitet tapılmadı!")
    
    if not db_university.raw_html:
        raise HTTPException(
            status_code=400, 
            detail="Bu universitet üçün skrap olunmuş xam HTML tapılmadı. Öncə scrape endpointini işə salın!"
        )
    
    try:
        # 3. Google Gemini SDK-nı konfiqurasiya edirik
        genai.configure(api_key=api_key)
        
        # 4. 🔥 İstədiyin model adını məhz burada birbaşa təyin edirik:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 5. Modelə gedəcək təlimat (Prompt)
        prompt = (
            f"Sən bir universitet skraper analitiksən. Aşağıdakı xam HTML mətnini analiz et "
            f"və mənə bu universitet haqqında tapdığın bütün mühüm məlumatları (ixtisaslar, "
            f"qəbul şərtləri, əlaqə) təmiz və oxunaqlı şəkildə çıxar:\n\n{db_university.raw_html}"
        )
        
        # 6. Sorğunu Google serverlərinə göndəririk
        response = model.generate_content(prompt)
        
        return {
            "status": "success",
            "university": db_university.name,
            "ai_analysis": response.text  # Gemini-dən gələn real cavab
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"AI Emalı zamanı real Google API xətası baş verdi: {str(e)}"
        )