from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Body
from sqlalchemy.orm import Session
from sqlalchemy import func
import urllib.request
import ssl

# Verilənlər bazası strukturlarımız
from .database import engine, get_db
from . import models, schemas, crud
from .config import CONFIDENCE_THRESHOLD
from .seed.seed_data import SEED_UNIVERSITIES, UPDATES

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

# Tətbiq qalxan kimi DB cədvəllərini yaradırıq (təmiz mühitdə də işləsin deyə)
models.Base.metadata.create_all(bind=engine)

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


def integrate_programs(db: Session, university_id: int, valid_programs: list):
    """Change Detector-i işə salır və nəticələri bazaya yazır (yeni/yenilənən).

    Həm canlı pipeline, həm də seed/simulyasiya endpointləri tərəfindən istifadə olunur.
    Geriyə (change_report, pending_count) qaytarır."""
    change_report = change_detector_agent.detect_changes(db, university_id, valid_programs)

    pending_count = 0
    for new_prog in change_report["new"]:
        # Etibarlılıq balı həddən aşağıdırsa, insan yoxlamasına (pending_review) göndərilir
        score = new_prog.get("confidence_score", 0.0)
        status = "approved" if score >= CONFIDENCE_THRESHOLD else "pending_review"
        if status == "pending_review":
            pending_count += 1

        db.add(models.Program(
            university_id=university_id,
            faculty=new_prog.get("faculty"),
            program_name=new_prog.get("program_name"),
            degree=new_prog.get("degree"),
            language=new_prog.get("language"),
            tuition_fee=new_prog.get("tuition_fee"),
            requirements=new_prog.get("requirements"),
            application_deadline=new_prog.get("application_deadline"),
            gpa_requirement=new_prog.get("gpa_requirement"),
            documents_required=new_prog.get("documents_required"),
            confidence_score=score,
            field_confidence=new_prog.get("field_confidence"),
            status=status
        ))

    for updated_prog in change_report["updated"]:
        db_prog_row = db.query(models.Program).filter(models.Program.id == updated_prog["id"]).first()
        if db_prog_row:
            # Dəyişmiş bütün izlənən sahələri yeniləyirik (yalnız fee deyil)
            db_prog_row.tuition_fee = updated_prog.get("tuition_fee")
            db_prog_row.language = updated_prog.get("language")
            db_prog_row.application_deadline = updated_prog.get("application_deadline")
            db_prog_row.gpa_requirement = updated_prog.get("gpa_requirement")
            db_prog_row.documents_required = updated_prog.get("documents_required")
            db_prog_row.requirements = updated_prog.get("requirements")
            db_prog_row.faculty = updated_prog.get("faculty")
            db_prog_row.confidence_score = updated_prog.get("confidence_score", db_prog_row.confidence_score)
            db_prog_row.field_confidence = updated_prog.get("field_confidence")
            db_prog_row.extracted_at = func.now()

    db.commit()
    return change_report, pending_count


def _synthetic_source(programs: list) -> str:
    """Fixture proqramlarından sintetik mənbə mətni qurur ki, validation source-match keçsin."""
    parts = []
    for p in programs:
        parts.extend(str(v) for v in p.values() if v is not None)
    return " ".join(parts)


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

    # STAGE 4: Extraction Agent
    raw_programs = extraction_agent.extract_programs(target_html)
    if not raw_programs:
        return {"status": "warning", "message": "İxtisas tapılmadı.", "reviewer_report": "[RƏDD EDİLDİ] Data boşdur."}

    # STAGE 5: Validation Agent — səhifə mətni ilə müqayisə + qayda-əsaslı confidence
    source_text = extraction_agent.clean_html(target_html)
    valid_programs = validation_agent.validate_data(raw_programs, source_text)

    # STAGE 6 & 7: Change Detector + Bazaya İnteqrasiya
    change_report, pending_count = integrate_programs(db, university_id, valid_programs)

    # Orta etibarlılıq balı (metrik)
    avg_confidence = (
        round(sum(p.get("confidence_score", 0) for p in valid_programs) / len(valid_programs), 3)
        if valid_programs else 0
    )

    # STAGE 8: Reviewer Agent (Yekun Hesabat)
    final_report = reviewer_agent.review_pipeline(
        university_name=db_university.name,
        target_url=target_url,
        total_valid=len(valid_programs),
        change_report=change_report,
        avg_confidence=avg_confidence,
        pending_count=pending_count
    )

    return {
        "status": "success",
        "university_name": db_university.name,
        "source_url_used": target_url,
        "metrics": {
            "total_processed": len(valid_programs),
            "new_added": len(change_report["new"]),
            "updated_fees": len(change_report["updated"]),
            "unchanged": change_report["unchanged_count"],
            "pending_count": pending_count,
            "avg_confidence": avg_confidence
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
            "degree": p.degree,
            "language": p.language,
            "tuition_fee": p.tuition_fee,
            "application_deadline": p.application_deadline,
            "gpa_requirement": p.gpa_requirement,
            "documents_required": p.documents_required,
            "confidence_score": p.confidence_score,
            "field_confidence": p.field_confidence
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

@app.post("/programs/{program_id}/reject", response_model=dict, tags=["Human Review Panel"])
def reject_program(program_id: int, db: Session = Depends(get_db)):
    """İdarəçi şübhəli məlumatı rədd edəndə statusu 'rejected' olaraq yeniləyir"""
    prog = db.query(models.Program).filter(models.Program.id == program_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Proqram tapılmadı")
    prog.status = "rejected"
    db.commit()
    return {"status": "success", "message": "Proqram rədd edildi."}


# =====================================================================
# 4. PROQRAM SİYAHISI VƏ DƏYİŞİKLİK TARİXÇƏSİ
# =====================================================================
@app.get("/universities/{university_id}/programs", response_model=list, tags=["Programs"])
def get_university_programs(university_id: int, db: Session = Depends(get_db)):
    """Universitetin bütün proqramlarını (frontend cədvəli üçün) qaytarır"""
    programs = db.query(models.Program).filter(models.Program.university_id == university_id).all()
    return [
        {
            "id": p.id,
            "faculty": p.faculty,
            "program_name": p.program_name,
            "degree": p.degree,
            "language": p.language,
            "tuition_fee": p.tuition_fee,
            "application_deadline": p.application_deadline,
            "gpa_requirement": p.gpa_requirement,
            "documents_required": p.documents_required,
            "confidence_score": p.confidence_score,
            "status": p.status
        } for p in programs
    ]

@app.get("/universities/{university_id}/changes", response_model=list, tags=["Programs"])
def get_university_changes(university_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """Köhnə↔yeni dəyişikliklərin auditini (müqayisə paneli üçün) qaytarır"""
    logs = (
        db.query(models.ChangeLog)
        .filter(models.ChangeLog.university_id == university_id)
        .order_by(models.ChangeLog.detected_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": c.id,
            "program_id": c.program_id,
            "program_name": c.program.program_name if c.program else None,
            "field_name": c.field_name,
            "old_value": c.old_value,
            "new_value": c.new_value,
            "detected_at": c.detected_at.isoformat() if c.detected_at else None
        } for c in logs
    ]


# =====================================================================
# 5. SEED & DƏYİŞİKLİK SİMULYASİYASI (DEV / DEMO — API açarı tələb etmir)
# =====================================================================
@app.post("/seed", response_model=dict, tags=["Seed / Demo"])
def seed_database(db: Session = Depends(get_db)):
    """Fixture datasından 6 universitet və 30+ proqramı bazaya yükləyir.

    Skrap/LLM tələb etmir — dashboard və dəyişiklik aşkarlama üçün təkrarlana bilən baza."""
    uni_count = 0
    total_programs = 0
    for uni in SEED_UNIVERSITIES:
        db_uni = db.query(models.University).filter(models.University.name == uni["name"]).first()
        if not db_uni:
            db_uni = models.University(name=uni["name"], website_url=uni["website_url"])
            db.add(db_uni)
            db.commit()
            db.refresh(db_uni)
            uni_count += 1

        source_text = _synthetic_source(uni["programs"])
        valid_programs = validation_agent.validate_data(uni["programs"], source_text)
        change_report, _ = integrate_programs(db, db_uni.id, valid_programs)
        total_programs += len(change_report["new"])

    return {
        "status": "success",
        "message": "Fixture datası yükləndi.",
        "universities_added": uni_count,
        "programs_added": total_programs,
    }


@app.post("/reset", response_model=dict, tags=["Seed / Demo"])
def reset_database(db: Session = Depends(get_db)):
    """Bütün məlumatı tam sıfırlayır (universitetlər, proqramlar, səhifələr, dəyişiklik jurnalı).

    Övladları əvvəl silirik ki, xarici açar (FK) məhdudiyyəti pozulmasın."""
    deleted = {
        "change_logs": db.query(models.ChangeLog).delete(),
        "programs": db.query(models.Program).delete(),
        "scraped_pages": db.query(models.ScrapedPage).delete(),
        "universities": db.query(models.University).delete(),
    }
    db.commit()
    return {"status": "success", "message": "Baza tam sıfırlandı.", "deleted": deleted}


@app.post("/universities/{university_id}/simulate-update", response_model=dict, tags=["Seed / Demo"])
def simulate_update(university_id: int, db: Session = Depends(get_db)):
    """Sonrakı bir 'skrap'ı təqlid edir (qiymət/son tarix dəyişikliyi + yeni ixtisas).

    Change Detection + ChangeLog + insan yoxlaması axınını API açarı olmadan göstərir."""
    db_uni = db.query(models.University).filter(models.University.id == university_id).first()
    if not db_uni:
        raise HTTPException(status_code=404, detail="Universitet tapılmadı!")

    updates = UPDATES.get(db_uni.name)
    if not updates:
        return {"status": "warning", "message": f"'{db_uni.name}' üçün simulyasiya datası yoxdur."}

    source_text = _synthetic_source(updates)
    valid_programs = validation_agent.validate_data(updates, source_text)
    change_report, pending_count = integrate_programs(db, university_id, valid_programs)

    return {
        "status": "success",
        "university_name": db_uni.name,
        "metrics": {
            "new_added": len(change_report["new"]),
            "updated_fields": len(change_report["updated"]),
            "unchanged": change_report["unchanged_count"],
            "pending_count": pending_count,
        },
    }