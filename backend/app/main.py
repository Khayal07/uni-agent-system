from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Body
from sqlalchemy.orm import Session
from sqlalchemy import func
import urllib.request
import ssl

# Verilənlər bazası strukturlarımız
from .database import SessionLocal, engine
from . import models, schemas, crud

# 5 Canavar Agentin importu
from .agents.research import ResearchAgent
from .agents.extraction import ExtractionAgent
from .agents.validation import ValidationAgent
from .agents.change_detector import ChangeDetectorAgent
from .agents.reviewer import ReviewerAgent

from fastapi.responses import HTMLResponse
import os

# Agentlərin instansiyalarını yaradırıq
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
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(req, context=context, timeout=15) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Sayt oxunarkən xəta baş verdi: {str(e)}")


# =====================================================================
# GET ENDPOINT-LƏRİ & FRONTEND SERVE
# =====================================================================

@app.get("/universities", response_model=list, tags=["Universities"])
def get_universities(db: Session = Depends(get_db)):
    universities = db.query(models.University).all()
    return [
        {"id": u.id, "name": u.name, "website_url": u.website_url} 
        for u in universities
    ]

@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
def serve_frontend():
    frontend_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(frontend_path):
        with open(frontend_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h2>UniAgent UI tapılmadı! index.html faylını yoxlayın.</h2>"


# =====================================================================
# UNİVERSİTET YARATMA ENDPOINT-İ
# =====================================================================
@app.post("/universities", response_model=dict, tags=["Universities"])
def create_university(
    name: str = Body(..., description="Universitetin adı"), 
    website_url: str = Body(..., description="Universitetin ana səhifə linki"), 
    db: Session = Depends(get_db)
):
    try:
        db_university = models.University(name=name, website_url=website_url)
        db.add(db_university)
        db.commit()
        db.refresh(db_university)
        return {
            "status": "success",
            "message": "Universitet uğurla bazaya qeyd edildi!",
            "university": {"id": db_university.id, "name": db_university.name, "website_url": db_university.website_url}
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Xəta: {str(e)}")


# =====================================================================
# MULTI-AGENT PIPELINE ENDPOINT-İ
# =====================================================================
@app.post("/universities/{university_id}/run-agent-pipeline", response_model=dict, tags=["Agent Pipeline"])
def run_university_agent_pipeline(university_id: int, db: Session = Depends(get_db)):
    db_university = db.query(models.University).filter(models.University.id == university_id).first()
    if not db_university:
        raise HTTPException(status_code=404, detail="Universitet bazada tapılmadı!")

    base_url = db_university.website_url
    print(f"\n[START PIPELINE] -> {db_university.name} prosesi başladı...")

    # STAGE 1 & 2: Scraping & Research Agent
    home_html = helper_scrape(base_url)
    target_url = research_agent.discover_specialty_url(home_html, base_url)
    
    # STAGE 3: Hədəf Səhifənin Skrapı
    target_html = helper_scrape(target_url) if target_url != base_url else home_html

    # Xam HTML-i audit üçün bazaya yadda saxlayırıq
    db_page = models.ScrapedPage(university_id=university_id, url=target_url, raw_html=target_html)
    db.add(db_page)

    # STAGE 4 & 5: Extraction & Validation Agents
    raw_programs = extraction_agent.extract_programs(target_html)
    if not raw_programs:
        return {"status": "warning", "message": "İxtisas tapılmadı.", "reviewer_report": "[RƏDD EDİLDİ] Data boşdur."}

    valid_programs = validation_agent.validate_data(raw_programs)

    # STAGE 6: Change Detector Agent
    change_report = change_detector_agent.detect_changes(db, university_id, valid_programs)

    # STAGE 7: Bazaya İnteqrasiya (Review & Validation Flow daxil)
    for new_prog in change_report["new"]:
        # Əgər etibarlılıq balı 0.75-dən aşağıdırsa, insan yoxlamasına (pending_review) göndər
        score = new_prog.get("confidence_score", 0.88)
        status = "approved" if score >= 0.75 else "pending_review"

        db_program = models.Program(
            university_id=university_id,
            faculty=new_prog.get("faculty"),
            program_name=new_prog.get("program_name"),
            degree=new_prog.get("degree"),
            language=new_prog.get("language"),
            tuition_fee=new_prog.get("tuition_fee"),
            requirements=new_prog.get("requirements"),
            confidence_score=score,
            status=status
        )
        db.add(db_program)

    for updated_prog in change_report["updated"]:
        db_prog_row = db.query(models.Program).filter(models.Program.id == updated_prog["id"]).first()
        if db_prog_row:
            db_prog_row.tuition_fee = updated_prog.get("tuition_fee")
            db_prog_row.confidence_score = updated_prog.get("confidence_score", 0.95)
            db_prog_row.extracted_at = func.now()

    db.commit()

    # STAGE 8: Reviewer Agent (Yekun Hesabat)
    final_report = reviewer_agent.review_pipeline(
        university_name=db_university.name,
        target_url=target_url,
        total_valid=len(valid_programs),
        change_report=change_report
    )

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


# =====================================================================
# 3. İNSAN TƏSDİQİ PANELSİNİN APİ ENDPOINT-LƏRİ
# =====================================================================
@app.get("/programs/pending", response_model=list, tags=["Human Review Panel"])
def get_pending_programs(db: Session = Depends(get_db)):
    """Təsdiq gözləyən (Aşağı etibarlılıqlı və ya yeni) proqramları frontendə ötürür"""
    pending = db.query(models.Program).filter(models.Program.status == "pending_review").all()
    return [
        {
            "id": p.id,
            "university_name": p.university.name,
            "program_name": p.program_name,
            "faculty": p.faculty,
            "tuition_fee": p.tuition_fee,
            "confidence_score": p.confidence_score
        } for p in pending
    ]

@app.post("/programs/{program_id}/approve", response_model=dict, tags=["Human Review Panel"])
def approve_program(program_id: int, db: Session = Depends(get_db)):
    """İdarəçi düyməni sıxanda statusu 'approved' olaraq yeniləyir"""
    prog = db.query(models.Program).filter(models.Program.id == program_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Proqram tapılmadı")
    prog.status = "approved"
    db.commit()
    return {"status": "success", "message": "Proqram insan tərəfindən uğurla təsdiqləndi!"}