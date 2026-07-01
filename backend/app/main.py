from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Body
from sqlalchemy.orm import Session
from sqlalchemy import func
import urllib.request
import ssl
import json
import time as _time

# Verilənlər bazası strukturlarımız
from .database import engine, get_db, SessionLocal
from . import models, schemas, crud
from .config import CONFIDENCE_THRESHOLD, DATABASE_URL
from .seed.seed_data import SEED_UNIVERSITIES, UPDATES

# 5 Canavar Agentin importu
from .agents.research import ResearchAgent
from .agents.extraction import ExtractionAgent
from .agents import crawler
from .agents.validation import ValidationAgent
from .agents.change_detector import ChangeDetectorAgent
from .agents.reviewer import ReviewerAgent

from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import os

# Frontend qovluğu: layihə kökündəki "frontend/" (backend/app-dan iki səviyyə yuxarı).
# Docker-də /frontend, lokal işlədikdə isə ../../frontend istifadə olunur.
_DOCKER_FRONTEND = "/frontend"
_LOCAL_FRONTEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
FRONTEND_DIR = _DOCKER_FRONTEND if os.path.isdir(_DOCKER_FRONTEND) else _LOCAL_FRONTEND

# Agentlərin instansiyalarını yaradırıq
research_agent = ResearchAgent()
extraction_agent = ExtractionAgent()
validation_agent = ValidationAgent()
change_detector_agent = ChangeDetectorAgent()
reviewer_agent = ReviewerAgent()

app = FastAPI(title="UniAgent: Multi-Agent University Data Pipeline")

# Statik frontend faylları (styles.css, app.js) /static altında verilir
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# SQLite dev-də sıfır-konfiqurasiya üçün cədvəlləri avtomatik yaradırıq.
# Postgres/managed mühitdə isə sxem Alembic (`alembic upgrade head`) tərəfindən idarə olunur
# — ikili yaratma konfliktini önləmək üçün create_all yalnız SQLite-də çağırılır.
if DATABASE_URL.startswith("sqlite"):
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


def integrate_programs(db: Session, university_id: int, valid_programs: list, source_url: str = None):
    """Change Detector-i işə salır və nəticələri bazaya yazır (yeni/yenilənən).

    Hər yeni/yenilənən proqram üçün `ProgramVersion` snapshot-u yazılır (tarixi versiyalama).
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

        db_prog = models.Program(
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
        )
        db.add(db_prog)
        db.flush()  # id almaq üçün
        crud.record_version(db, db_prog, source_url)  # ilkin (v1) snapshot

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
            crud.record_version(db, db_prog_row, source_url)  # yeni versiya snapshot-u

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
    frontend_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(frontend_path):
        with open(frontend_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h2>UniAgent UI tapılmadı! index.html faylını yoxlayın.</h2>"


@app.get("/database", response_class=HTMLResponse, tags=["Frontend"])
def serve_database_page():
    """Tam baza görünüşü səhifəsi (bütün cədvəllər)."""
    page_path = os.path.join(FRONTEND_DIR, "database.html")
    if os.path.exists(page_path):
        with open(page_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h2>database.html tapılmadı!</h2>"


@app.get("/api/database", response_model=dict, tags=["Database"])
def dump_database(db: Session = Depends(get_db)):
    """Bütün cədvəlləri (scraped_pages istisna) JSON kimi qaytarır — tam baza görünüşü üçün."""
    universities = db.query(models.University).all()
    programs = db.query(models.Program).all()
    changes = db.query(models.ChangeLog).order_by(models.ChangeLog.detected_at.desc()).all()

    # program_id → program_name xəritəsi (jurnalda oxunaqlı ad üçün)
    prog_name = {p.id: p.program_name for p in programs}

    return {
        "universities": [
            {"id": u.id, "name": u.name, "website_url": u.website_url,
             "created_at": str(u.created_at) if u.created_at else None}
            for u in universities
        ],
        "programs": [
            {"id": p.id, "university_id": p.university_id, "faculty": p.faculty,
             "program_name": p.program_name, "degree": p.degree, "language": p.language,
             "tuition_fee": p.tuition_fee, "application_deadline": p.application_deadline,
             "gpa_requirement": p.gpa_requirement, "documents_required": p.documents_required,
             "requirements": p.requirements, "confidence_score": p.confidence_score,
             "status": p.status, "extracted_at": str(p.extracted_at) if p.extracted_at else None}
            for p in programs
        ],
        "change_logs": [
            {"id": c.id, "program_id": c.program_id, "program_name": prog_name.get(c.program_id),
             "university_id": c.university_id, "field_name": c.field_name,
             "old_value": c.old_value, "new_value": c.new_value,
             "detected_at": str(c.detected_at) if c.detected_at else None}
            for c in changes
        ],
        "counts": {
            "universities": len(universities),
            "programs": len(programs),
            "change_logs": len(changes),
        },
    }


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
def _run_pipeline_task(university_id: int, run_id: int):
    """Pipeline-ı arxa planda (background task) icra edir və hər agent addımını
    `AgentStep` kimi yazır — real-time monitoring bu qeydləri SSE ilə oxuyur.

    Öz DB sessiyasını açır (background task ayrı sapda işləyir)."""
    db = SessionLocal()
    current_step = None
    try:
        db_university = db.query(models.University).filter(models.University.id == university_id).first()
        base_url = db_university.website_url
        print(f"\n[START PIPELINE] -> {db_university.name} (run {run_id}) prosesi başladı...")

        # STEP 1: Research — skrap + heuristik link seçimi
        current_step = crud.start_step(db, run_id, "research", input_summary=base_url)
        home_html = crawler.fetch(base_url)
        sitemap = crawler.discover_sitemap_urls(base_url)
        hrefs = research_agent.extract_all_links(home_html, base_url)
        candidates = crawler.rank_candidate_urls(hrefs, sitemap, base_url)
        pages_html = [home_html]
        for url in candidates[:5]:
            html = crawler.fetch(url)
            if html:
                pages_html.append(html)
                db.add(models.ScrapedPage(university_id=university_id, url=url, raw_html=html))
        db.commit()
        target_url = candidates[0] if candidates else base_url
        combined_html = "\n".join(pages_html)
        crud.finish_step(db, current_step, output_summary=f"{len(candidates)} namizəd səhifə · hədəf: {target_url}")

        # STEP 2: Extraction
        current_step = crud.start_step(db, run_id, "extraction", input_summary=f"HTML {len(combined_html)} simvol")
        raw_programs = extraction_agent.extract_programs(combined_html)
        crud.finish_step(db, current_step, output_summary=f"{len(raw_programs)} xam ixtisas çıxarıldı")
        if not raw_programs:
            run = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
            crud.finish_run(db, run, "success",
                            metrics={"total_processed": 0, "note": "no_programs", "source_url_used": target_url})
            return

        # STEP 3: Validation
        current_step = crud.start_step(db, run_id, "validation", input_summary=f"{len(raw_programs)} ixtisas")
        source_text = extraction_agent.clean_html(combined_html)
        valid_programs = validation_agent.validate_data(raw_programs, source_text)
        avg_confidence = (
            round(sum(p.get("confidence_score", 0) for p in valid_programs) / len(valid_programs), 3)
            if valid_programs else 0
        )
        crud.finish_step(db, current_step, output_summary=f"{len(valid_programs)} keçdi · orta etibar {avg_confidence}")

        # STEP 4: Change Detection + inteqrasiya (versiyalama daxil)
        current_step = crud.start_step(db, run_id, "change", input_summary=f"{len(valid_programs)} ixtisas")
        change_report, pending_count = integrate_programs(db, university_id, valid_programs, target_url)
        crud.finish_step(
            db, current_step,
            output_summary=f"yeni {len(change_report['new'])} · yenilənən {len(change_report['updated'])} · gözləyən {pending_count}",
        )

        # STEP 5: Review
        current_step = crud.start_step(db, run_id, "review")
        final_report = reviewer_agent.review_pipeline(
            university_name=db_university.name, target_url=target_url,
            total_valid=len(valid_programs), change_report=change_report,
            avg_confidence=avg_confidence, pending_count=pending_count,
        )
        crud.finish_step(db, current_step, output_summary="Yekun hesabat imzalandı", log_text=final_report)

        metrics = {
            "total_processed": len(valid_programs),
            "new_added": len(change_report["new"]),
            "updated_fees": len(change_report["updated"]),
            "unchanged": change_report["unchanged_count"],
            "pending_count": pending_count,
            "avg_confidence": avg_confidence,
            "university_name": db_university.name,
            "source_url_used": target_url,
            "reviewer_report": final_report,
        }
        run = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
        crud.finish_run(db, run, "success", metrics=metrics)
        print(f"[PIPELINE run {run_id}] uğurla bitdi.")
    except Exception as e:
        db.rollback()
        if current_step is not None:
            try:
                crud.finish_step(db, current_step, status="failed", log_text=str(e))
            except Exception:
                db.rollback()
        run = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
        if run:
            crud.finish_run(db, run, "failed", error=str(e))
        print(f"[PIPELINE run {run_id}] XƏTA: {e}")
    finally:
        db.close()


@app.post("/universities/{university_id}/run-agent-pipeline", response_model=dict, tags=["Agent Pipeline"])
def run_university_agent_pipeline(university_id: int, background_tasks: BackgroundTasks,
                                  db: Session = Depends(get_db)):
    """Pipeline-ı arxa planda başladır və dərhal `run_id` qaytarır.

    Frontend `run_id` ilə `/runs/{run_id}/stream` (SSE) açıb agentləri real-time izləyir."""
    db_university = db.query(models.University).filter(models.University.id == university_id).first()
    if not db_university:
        raise HTTPException(status_code=404, detail="Universitet bazada tapılmadı!")

    run = crud.start_run(db, university_id, run_type="live")
    background_tasks.add_task(_run_pipeline_task, university_id, run.id)
    return {"status": "started", "run_id": run.id, "university_name": db_university.name}


def _run_snapshot(db: Session, run_id: int) -> dict:
    """Bir icranın cari vəziyyətini (run + addımlar) JSON kimi qaytarır."""
    run = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
    if not run:
        return None
    steps = [
        {"agent_name": s.agent_name, "status": s.status,
         "duration_ms": s.duration_ms, "output_summary": s.output_summary,
         "log_text": s.log_text}
        for s in run.steps
    ]
    return {
        "run_id": run.id, "status": run.status, "run_type": run.run_type,
        "metrics": run.metrics_json, "error": run.error_text, "steps": steps,
    }


@app.get("/runs/{run_id}", response_model=dict, tags=["Agent Pipeline"])
def get_run(run_id: int, db: Session = Depends(get_db)):
    """Polling fallback — icranın cari vəziyyəti."""
    snap = _run_snapshot(db, run_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="Run tapılmadı")
    return snap


@app.get("/runs/{run_id}/stream", tags=["Agent Pipeline"])
def stream_run(run_id: int):
    """SSE axını — icra bitənə qədər agent addımlarını real-time ötürür."""
    def event_gen():
        last_payload = None
        for _ in range(600):  # ~5 dəq təhlükəsizlik limiti
            db = SessionLocal()
            try:
                snap = _run_snapshot(db, run_id)
            finally:
                db.close()
            if snap is None:
                yield f"event: error\ndata: {json.dumps({'detail': 'run not found'})}\n\n"
                return
            payload = json.dumps(snap, ensure_ascii=False)
            if payload != last_payload:
                yield f"data: {payload}\n\n"
                last_payload = payload
            if snap["status"] in ("success", "failed"):
                yield f"event: done\ndata: {payload}\n\n"
                return
            _time.sleep(0.8)
        yield f"event: done\ndata: {json.dumps({'status': 'timeout'})}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


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


# Redaktə/diff üçün izlənən sahələr
_EDITABLE_FIELDS = [
    "faculty", "program_name", "degree", "language", "tuition_fee",
    "requirements", "application_deadline", "gpa_requirement", "documents_required",
]


@app.get("/programs/{program_id}/diff", response_model=dict, tags=["Human Review Panel"])
def get_program_diff(program_id: int, db: Session = Depends(get_db)):
    """Proqramın cari versiyasını əvvəlki versiya ilə sahə-sahə müqayisə edir.

    Side-by-side review ekranı üçün — hər sahə üçün (old, new, changed) qaytarır.
    Əvvəlki versiya yoxdursa (ilk snapshot), old=null, changed=False."""
    prog = db.query(models.Program).filter(models.Program.id == program_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Proqram tapılmadı")

    versions = (
        db.query(models.ProgramVersion)
        .filter(models.ProgramVersion.program_id == program_id)
        .order_by(models.ProgramVersion.version_no.desc())
        .all()
    )
    current = versions[0] if versions else None
    previous = versions[1] if len(versions) > 1 else None

    fields = {}
    for f in _EDITABLE_FIELDS:
        new_val = getattr(current, f, None) if current else getattr(prog, f, None)
        old_val = getattr(previous, f, None) if previous else None
        changed = previous is not None and (str(old_val or "") != str(new_val or ""))
        fields[f] = {"old": old_val, "new": new_val, "changed": changed}

    return {
        "program_id": program_id,
        "program_name": prog.program_name,
        "university_name": prog.university.name if prog.university else None,
        "confidence_score": prog.confidence_score,
        "field_confidence": prog.field_confidence,
        "status": prog.status,
        "current_version_no": current.version_no if current else None,
        "previous_version_no": previous.version_no if previous else None,
        "source_url": current.source_url if current else None,
        "fields": fields,
    }


@app.patch("/programs/{program_id}", response_model=dict, tags=["Human Review Panel"])
def edit_program(program_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """İdarəçi qeydi düzəldəndə sahələri yeniləyir və yeni versiya snapshot-u yazır.

    Yalnız `_EDITABLE_FIELDS` daxilindəki açarlar qəbul edilir. Redaktədən sonra
    istəyə görə status da (approved/pending_review/rejected) təyin oluna bilər."""
    prog = db.query(models.Program).filter(models.Program.id == program_id).first()
    if not prog:
        raise HTTPException(status_code=404, detail="Proqram tapılmadı")

    for key, value in payload.items():
        if key in _EDITABLE_FIELDS:
            setattr(prog, key, value)
    new_status = payload.get("status")
    if new_status in ("approved", "pending_review", "rejected"):
        prog.status = new_status

    prog.extracted_at = func.now()
    crud.record_version(db, prog, source_url="manual-edit")  # redaktə də tarixçəyə düşür
    db.commit()
    return {"status": "success", "message": "Proqram redaktə olundu və yeni versiya yazıldı.",
            "program_id": program_id}


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