import os
import requests  # 👈 SDK yox, sadəcə requests istifadə edirik!
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, schemas
from app.database import get_db

router = APIRouter()

# ... digər universitet və scrape endpointlərin olduğu kimi qalır ...

@router.post("/universities/{university_id}/process-with-ai/")
def process_html_with_gemini(university_id: int, db: Session = Depends(get_db)):
    """Google Gemini API-ni rəsmi SDK olmadan, birbaşa HTTP POST ilə çağırır"""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() == "" or api_key == "bura_yaz":
        raise HTTPException(
            status_code=400, 
            detail="Zəhmət olmasa .env faylında real GEMINI_API_KEY təyin edin!"
        )
    
    db_university = crud.get_university(db, university_id=university_id)
    if not db_university:
        raise HTTPException(status_code=404, detail="Universitet tapılmadı!")
    
    if not db_university.raw_html:
        raise HTTPException(
            status_code=400, 
            detail="Bu universitet üçün skrap olunmuş xam HTML tapılmadı. Öncə scrape endpointini işə salın!"
        )
    
    try:
        # 🔥 Google Gemini-nin rəsmi birbaşa HTTP URL-i
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        prompt = (
            f"Sən bir universitet skraper analitiksən. Aşağıdakı xam HTML mətnini analiz et "
            f"və mənə bu universitet haqqında tapdığın bütün mühüm məlumatları (ixtisaslar, "
            f"qəbul şərtləri, təhsil haqları) təmiz və oxunaqlı şəkildə çıxar:\n\n{db_university.raw_html}"
        )
        
        # Google API-nin birbaşa qəbul etdiyi JSON strukturu
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }
        
        # Sorğunu birbaşa göndəririk
        response = requests.post(url, json=payload, headers=headers)
        
        # Əgər Google tərəfindən hər hansı bir xəta kodu qayıtsa, onu tuturuq
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Google API birbaşa xəta qaytardı: {response.text}"
            )
            
        res_data = response.json()
        
        # Cavabın içindən mətni təmiz şəkildə çıxarırıq
        ai_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
        
        return {
            "status": "success",
            "university": db_university.name,
            "ai_analysis": ai_text
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Birbaşa HTTP sorğusu zamanı xəta yarandı: {str(e)}"
        )