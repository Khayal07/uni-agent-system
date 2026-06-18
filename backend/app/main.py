from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Body
from sqlalchemy.orm import Session
from sqlalchemy import func
import urllib.request
import ssl

# Bizim verilənlər bazası strukturlarımız
from .database import SessionLocal, engine
from . import models, schemas, crud

# Sənin yazdığın o 5 canavar agentin bura importu
from .agents.research import ResearchAgent
from .agents.extraction import ExtractionAgent
from .agents.validation import ValidationAgent
from .agents.change_detector import ChangeDetectorAgent
from .agents.reviewer import ReviewerAgent

from fastapi.responses import HTMLResponse
import os

# Agentlərin instansiyalarını (instance) yaradırıq
research_agent = ResearchAgent()
extraction_agent = ExtractionAgent()
validation_agent = ValidationAgent()
change_detector_agent = ChangeDetectorAgent()
reviewer_agent = ReviewerAgent()

app = FastAPI(title="UniAgent: Multi-Agent University Data Pipeline")

# DB Sessiyası üçün dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def helper_scrape(url: str) -> str:
    """Universitet saytından bloklanmadan xam HTML çəkən köməkçi funksiya"""
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        # SSL sertifikat problemlərini keçmək üçün
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(req, context=context, timeout=15) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Sayt oxunarkən xəta baş verdi: {str(e)}")


# =====================================================================
# FRONTEND ÜÇÜN LAZIM OLAN GET ENDPOINT-LƏRİ
# =====================================================================

@app.get("/universities", response_model=list, tags=["Universities"])
def get_universities(db: Session = Depends(get_db)):
    """Bazadakı bütün universitetlərin siyahısını frontend üçün qaytarır"""
    universities = db.query(models.University).all()
    return [
        {"id": u.id, "name": u.name, "website_url": u.website_url} 
        for u in universities
    ]

@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
def serve_frontend():
    """Ana səhifəyə daxil qorunanda bizim qəşəng UI-ı ekrana basır"""
    # HTML faylını birbaşa oxuyub brauzerə göndəririk
    frontend_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(frontend_path):
        with open(frontend_path, "r", encoding="utf-8") as f:
            return f.read()
    return """
    <body style="font-family:sans-serif; background:#111827; color:#fff; text-align:center; padding-top:50px;">
        <h2>UniAgent UI-a Xoş Gəlmisiniz!</h2>
        <p>Zəhmət olmasa main.py ilə eyni qovluqda 'index.html' faylını yaradın.</p>
    </body>
    """

# =====================================================================
# 1. YENİ ƏLAVƏ OLUNAN HİSSƏ: UNİVERSİTET YARATMA (CRUD) ENDPOINT-İ
# =====================================================================
@app.post("/universities", response_model=dict, tags=["Universities"])
def create_university(
    name: str = Body(..., description="Universitetin adı (Məsələn: UNEC)"), 
    website_url: str = Body(..., description="Universitetin ana səhifə linki"), 
    db: Session = Depends(get_db)
):
    """
    Sistemə və verilənlər bazasına yeni universitet qeydiyyatdan keçirir 🏫
    """
    try:
        # Pipeline-dakı website_url sütun adı ilə tam eyniləşdirildi
        db_university = models.University(name=name, website_url=website_url)
        db.add(db_university)
        db.commit()
        db.refresh(db_university)
        
        print(f"[DB SUCCESS] -> {name} bazaya əlavə edildi. ID: {db_university.id}")
        
        return {
            "status": "success",
            "message": "Universitet uğurla bazaya qeyd edildi!",
            "university": {
                "id": db_university.id,
                "name": db_university.name,
                "website_url": db_university.website_url
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Universitet bazaya yazıla bilmədi: {str(e)}")


# =====================================================================
# 2. SƏNİN REZULTAT VERƏN MULTI-AGENT ENDPOINT-İN
# =====================================================================
@app.post("/universities/{university_id}/run-agent-pipeline", response_model=dict, tags=["Agent Pipeline"])
def run_university_agent_pipeline(university_id: int, db: Session = Depends(get_db)):
    """
    RƏSMƏN MULTI-AGENT ZƏNCİRİNİ BAŞLADAN ƏSAS ENDPOINT 🔥
    """
    # 1. Universitet məlumatını bazadan çəkirik
    db_university = db.query(models.University).filter(models.University.id == university_id).first()
    if not db_university:
        raise HTTPException(status_code=404, detail="Universitet bazada tapılmadı!")

    base_url = db_university.website_url
    print(f"\n[START PIPELINE] -> {db_university.name} üçün proses başladıldı...")

    # ==========================================
    # STAGE 1: ANA SƏHİFƏNİN SKRAP EDİLMƏSİ
    # ==========================================
    home_html = helper_scrape(base_url)

    # ==========================================
    # STAGE 2: RESEARCH AGENT (Kəşfiyyat)
    # ==========================================
    # Agent ana səhifədəki linkləri gəzir və ixtisas olan səhifəni təyin edir
    target_url = research_agent.discover_specialty_url(home_html, base_url)
    
    # ==========================================
    # STAGE 3: HƏDƏF SƏHİFƏNİN SKRAP EDİLMƏSİ
    # ==========================================
    # Əgər fərqli alt link tapıbsa, oranı skrap edirik, tapmayıbsa elə ana səhifəni
    if target_url != base_url:
        print(f"[Pipeline]: Alt səhifə skrap edilir -> {target_url}")
        target_html = helper_scrape(target_url)
    else:
        target_html = home_html

    # ==========================================
    # STAGE 4: EXTRACTION AGENT (Məlumat Çıxarma)
    # ==========================================
    raw_programs = extraction_agent.extract_programs(target_html)
    if not raw_programs:
        return {
            "status": "warning",
            "message": "Model mətndən heç bir ixtisas qopara bilmədi.",
            "reviewer_report": "[RƏDD EDİLDİ] Data tapılmadı."
        }

    # ==========================================
    # STAGE 5: VALIDATION AGENT (Məlumat Yoxlaması)
    # ==========================================
    valid_programs = validation_agent.validate_data(raw_programs)

    # ==========================================
    # STAGE 6: CHANGE DETECTOR AGENT (Dəyişiklik Təyini)
    # ==========================================
    change_report = change_detector_agent.detect_changes(db, university_id, valid_programs)

    # ==========================================
    # STAGE 7: BAZAYA YAZILMA (INTEGRATION)
    # ==========================================
    # A) Tamamilə yeni ixtisasları əlavə edirik
    for new_prog in change_report["new"]:
        db_program = models.Program(
            university_id=university_id,
            faculty=new_prog.get("faculty"),
            program_name=new_prog.get("program_name"),
            degree=new_prog.get("degree"),
            language=new_prog.get("language"),
            tuition_fee=new_prog.get("tuition_fee"),
            requirements=new_prog.get("requirements")
        )
        db.add(db_program)

    # B) Qiyməti dəyişən ixtisasları UPDATE edirik
    for updated_prog in change_report["updated"]:
        db_prog_row = db.query(models.Program).filter(models.Program.id == updated_prog["id"]).first()
        if db_prog_row:
            db_prog_row.tuition_fee = updated_prog.get("tuition_fee")
            # Qiymət dəyişəndə zaman damğasını yeniləyirik
            db_prog_row.extracted_at = func.now()

    db.commit()

    # ==========================================
    # STAGE 8: REVIEWER AGENT (Yekun Hesabat)
    # ==========================================
    final_report = reviewer_agent.review_pipeline(
        university_name=db_university.name,
        target_url=target_url,
        total_valid=len(valid_programs),
        change_report=change_report
    )

    print(f"[PIPELINE SUCCESS] -> Proses uğurla başa çatdı.\n")

    # İdarəçi heyətinə və ya Frontend-ə qaytarılacaq yekun cavab
    return {
        "status": "success",
        "university_name": db_university.name,
        "source_url_used": target_url,
        "metrics": {
            "total_processed": len(valid_programs),
            "new_added": len(change_report["new"]),
            "updated_fees": len(change_report["updated"]),
            "unchanged": change_report["unchanged_count"]
        },
        "reviewer_report": final_report
    }