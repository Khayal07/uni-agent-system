import os
import requests
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
    
    # Sınaq məqsədli xam HTML simulyasiyası
    sample_html = """
    <html>
        <body>
            <h1>Xəzər Universiteti</h1>
            <p>İxtisaslar: Kompüter Mühəndisliyi, İT, Süni İntellekt.</p>
            <p>Təhsil haqqı: 5000 AZN</p>
            <p>Son müraciət tarixi: 31 Avqust 2026</p>
        </body>
    </html>
    """
    db_university.raw_html = sample_html
    db.commit()
    db.refresh(db_university)
    
    return {"status": "success", "message": "Xam HTML simulyasiya olundu və bazaya uğurla yazıldı!"}


# 🔥 YENİ: OPENROUTER İLƏ DEEPSEEK ANALİZ ENDPOINTI
@router.post("/universities/{university_id}/process-with-ai/")
def process_html_with_openrouter(university_id: int, db: Session = Depends(get_db)):
    """Bazadakı HTML məlumatını OpenRouter vasitəsilə DeepSeek modelinə göndərib analiz edir"""
    
    # 1. .env-dən gələn OpenRouter açarını yoxlayırıq
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or api_key.strip() == "":
        raise HTTPException(
            status_code=400, 
            detail="Zəhmət olmasa .env faylında real OPENROUTER_API_KEY təyin edin!"
        )
    
    # 2. Bazadan universiteti çəkirik
    db_university = crud.get_university(db, university_id=university_id)
    if not db_university:
        raise HTTPException(status_code=404, detail="Universitet tapılmadı!")
    
    # 3. HTML verilənlərini yoxlayırıq
    if not db_university.raw_html:
        raise HTTPException(
            status_code=400, 
            detail="Bu universitet üçün skrap olunmuş xam HTML tapılmadı. Öncə scrape endpointini işə salın!"
        )
    
    try:
        # OpenRouter-in standart rəsmi API URL-i
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        # OpenRouter qaydalarına uyğun Header strukturu
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000", # OpenRouter statistikası üçün mütləq deyil amma yaxşı olar
            "X-Title": "University Agent System"
        }
        
        prompt = (
            f"Sən bir universitet skraper analitiksən. Aşağıdakı xam HTML mətnini analiz et "
            f"və mənə bu universitet haqqında tapdığın bütün mühüm məlumatları (ixtisaslar, "
            f"qəbul şərtləri, təhsil haqları) təmiz və oxunaqlı şəkildə çıxar:\n\n{db_university.raw_html}"
        )
        
        # Standart OpenAI/OpenRouter JSON Payload formatı
        payload = {
            "model": "deepseek/deepseek-r1:free",  # 🔥 İstifadə edəcəyimiz PULSUZ DeepSeek modeli
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # Sorğunu göndəririk
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"OpenRouter API xəta qaytardı: {response.text}"
            )
            
        res_data = response.json()
        
        # OpenRouter-dən gələn standart cavab mətnini çıxarırıq
        ai_text = res_data["choices"][0]["message"]["content"]
        
        return {
            "status": "success",
            "university": db_university.name,
            "ai_analysis": ai_text
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"OpenRouter ilə əlaqə zamanı gözlənilməz xəta: {str(e)}"
        )