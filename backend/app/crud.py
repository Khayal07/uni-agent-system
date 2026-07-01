import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from . import models, schemas

# Məzmun barmaq izinə (content_hash) daxil olan sahələr — versiyalama/dedupe üçün
VERSIONED_FIELDS = [
    "faculty", "program_name", "degree", "language", "tuition_fee",
    "requirements", "application_deadline", "gpa_requirement", "documents_required",
]


def compute_content_hash(prog) -> str:
    """Proqramın izlənən sahələrindən deterministik SHA-256 barmaq izi qurur.

    `prog` ya model obyekti, ya da dict ola bilər."""
    getter = (lambda f: prog.get(f)) if isinstance(prog, dict) else (lambda f: getattr(prog, f, None))
    joined = "|".join(str(getter(f) or "").strip().lower() for f in VERSIONED_FIELDS)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def record_version(db: Session, program: "models.Program", source_url: str = None) -> "models.ProgramVersion":
    """Proqram üçün yeni snapshot yazır; köhnə cari versiyanı bağlayır (valid_to + is_current=False).

    `Program.current_version_id` və `content_hash` yenilənir. commit çağıran tərəfdə edilir."""
    # Əvvəlki cari versiyanı bağla
    prev = (
        db.query(models.ProgramVersion)
        .filter(
            models.ProgramVersion.program_id == program.id,
            models.ProgramVersion.is_current.is_(True),
        )
        .all()
    )
    next_no = 1
    for v in prev:
        v.is_current = False
        v.valid_to = datetime.utcnow()
        next_no = max(next_no, v.version_no + 1)

    chash = compute_content_hash(program)
    version = models.ProgramVersion(
        program_id=program.id,
        version_no=next_no,
        faculty=program.faculty,
        program_name=program.program_name,
        degree=program.degree,
        language=program.language,
        tuition_fee=program.tuition_fee,
        requirements=program.requirements,
        application_deadline=program.application_deadline,
        gpa_requirement=program.gpa_requirement,
        documents_required=program.documents_required,
        confidence_score=program.confidence_score,
        field_confidence=program.field_confidence,
        content_hash=chash,
        source_url=source_url,
        valid_from=datetime.utcnow(),
        is_current=True,
    )
    db.add(version)
    db.flush()  # version.id-ni almaq üçün
    program.current_version_id = version.id
    program.content_hash = chash
    return version


# --- Agent Run / Step audit helper-ləri ---
def start_run(db: Session, university_id: int, run_type: str = "live") -> "models.AgentRun":
    run = models.AgentRun(university_id=university_id, run_type=run_type, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def finish_run(db: Session, run: "models.AgentRun", status: str, metrics: dict = None, error: str = None):
    run.status = status
    run.finished_at = datetime.utcnow()
    if metrics is not None:
        run.metrics_json = metrics
    if error is not None:
        run.error_text = error
    db.commit()


def start_step(db: Session, run_id: int, agent_name: str, input_summary: str = None) -> "models.AgentStep":
    step = models.AgentStep(
        run_id=run_id, agent_name=agent_name, status="running", input_summary=input_summary
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def finish_step(db: Session, step: "models.AgentStep", status: str = "done",
                output_summary: str = None, log_text: str = None):
    step.status = status
    step.finished_at = datetime.utcnow()
    if step.started_at:
        step.duration_ms = int((step.finished_at - step.started_at).total_seconds() * 1000)
    if output_summary is not None:
        step.output_summary = output_summary
    if log_text is not None:
        step.log_text = log_text
    db.commit()

# Universitet əlavə etmək
def create_university(db: Session, university: schemas.UniversityCreate):
    db_uni = models.University(name=university.name, website_url=university.website_url)
    db.add(db_uni)
    db.commit()
    db.refresh(db_uni)
    return db_uni

# Universitetləri siyahılamaq
def get_universities(db: Session, skip: int = 0, limit: int = 10):
    return db.query(models.University).offset(skip).limit(limit).all()

# Proqram (İxtisas) əlavə etmək
def create_program(db: Session, program: schemas.ProgramCreate):
    db_program = models.Program(**program.model_dump())
    db.add(db_program)
    db.commit()
    db.refresh(db_program)
    return db_program

# Xam HTML səhifəni bazaya yadda saxlamaq (Scraper üçün)
def save_scraped_page(db: Session, university_id: int, url: str, html_content: str):
    db_page = models.ScrapedPage(
        university_id=university_id,
        url=url,
        raw_html=html_content
    )
    db.add(db_page)
    db.commit()
    db.refresh(db_page)
    return db_page