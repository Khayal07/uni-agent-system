from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float, Boolean, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class University(Base):
    __tablename__ = "universities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    website_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Əlaqələr (Relationships)
    pages = relationship("ScrapedPage", back_populates="university", cascade="all, delete-orphan")
    programs = relationship("Program", back_populates="university", cascade="all, delete-orphan")


class ScrapedPage(Base):
    __tablename__ = "scraped_pages"

    id = Column(Integer, primary_key=True, index=True)
    university_id = Column(Integer, ForeignKey("universities.id"))
    url = Column(String, nullable=False)
    raw_html = Column(Text, nullable=True)  # Skrap olunmuş xam kontent
    scraped_at = Column(DateTime, default=datetime.utcnow)

    university = relationship("University", back_populates="pages")


class Program(Base):
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, index=True)
    university_id = Column(Integer, ForeignKey("universities.id"))
    faculty = Column(String, nullable=True)      # Məs: İnformasiya Texnologiyaları
    program_name = Column(String, nullable=False) # Məs: Süni İntellekt Mühəndisliyi
    degree = Column(String, nullable=True)        # Bachelor, Master, PhD
    language = Column(String, nullable=True)     # English, Azerbaijani və s.
    tuition_fee = Column(String, nullable=True)  # Təhsil haqqı qiyməti
    requirements = Column(Text, nullable=True)   # Qəbul şərtləri (ümumi qeyd)

    # Spec-in tələb etdiyi ayrıca məlumat sahələri
    application_deadline = Column(String, nullable=True)  # Müraciət son tarixi
    gpa_requirement = Column(String, nullable=True)       # Minimum GPA tələbi
    documents_required = Column(Text, nullable=True)      # Tələb olunan sənədlər

    extracted_at = Column(DateTime, default=datetime.utcnow)

    confidence_score = Column(Float, nullable=True, default=1.0)
    # Sahə-səviyyə etibarlılıq balları (validation evidence) — JSON mətn kimi saxlanır
    field_confidence = Column(Text, nullable=True)
    status = Column(String, nullable=True, default="approved")  # approved, pending_review, rejected

    # Cari (current) versiyanın id-si və məzmun barmaq izi (dəyişməz aşkarlama / dedupe üçün).
    # current_version_id dairəvi FK yaratmamaq üçün sadə Integer pointer-dir.
    current_version_id = Column(Integer, nullable=True)
    content_hash = Column(String, nullable=True, index=True)

    university = relationship("University", back_populates="programs")
    versions = relationship(
        "ProgramVersion", back_populates="program",
        cascade="all, delete-orphan", order_by="ProgramVersion.version_no",
    )

    __table_args__ = (
        Index("ix_programs_uni_name_degree", "university_id", "program_name", "degree"),
    )


class ProgramVersion(Base):
    """Proqramın tam snapshot-u — tarixi versiyalama (change detection-un əsl mənbəyi).

    Hər dəyişiklikdə köhnə cari versiya `valid_to` + `is_current=False` alır, yenisi yazılır.
    `Program` cari vəziyyəti, `ProgramVersion` isə bütün tarixçəni saxlayır."""
    __tablename__ = "program_versions"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), index=True)
    version_no = Column(Integer, nullable=False, default=1)

    # Snapshot sahələri (Program ilə eyni)
    faculty = Column(String, nullable=True)
    program_name = Column(String, nullable=False)
    degree = Column(String, nullable=True)
    language = Column(String, nullable=True)
    tuition_fee = Column(String, nullable=True)
    requirements = Column(Text, nullable=True)
    application_deadline = Column(String, nullable=True)
    gpa_requirement = Column(String, nullable=True)
    documents_required = Column(Text, nullable=True)

    confidence_score = Column(Float, nullable=True)
    field_confidence = Column(Text, nullable=True)
    content_hash = Column(String, nullable=True)
    source_url = Column(String, nullable=True)  # Bu snapshot-un çıxarıldığı mənbə linki

    valid_from = Column(DateTime, default=datetime.utcnow)
    valid_to = Column(DateTime, nullable=True)          # Növbəti versiya gələnə qədər null
    is_current = Column(Boolean, default=True, index=True)

    program = relationship("Program", back_populates="versions")

    __table_args__ = (
        Index("ix_program_versions_prog_current", "program_id", "is_current"),
    )


class AgentRun(Base):
    """Pipeline icrasının auditi — real-time monitoring və audit trail üçün üst səviyyə."""
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    university_id = Column(Integer, ForeignKey("universities.id", ondelete="CASCADE"), index=True)
    run_type = Column(String, nullable=False, default="live")  # live, simulate, seed
    status = Column(String, nullable=False, default="running")  # running, success, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    metrics_json = Column(JSON, nullable=True)   # Postgres-də JSONB, SQLite-də mətn
    error_text = Column(Text, nullable=True)

    steps = relationship(
        "AgentStep", back_populates="run",
        cascade="all, delete-orphan", order_by="AgentStep.id",
    )


class AgentStep(Base):
    """Bir agentin bir addımı — real-time SSE monitorunun oxuduğu qeyd."""
    __tablename__ = "agent_steps"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    agent_name = Column(String, nullable=False)   # research, extraction, validation, change, review
    status = Column(String, nullable=False, default="running")  # running, done, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    log_text = Column(Text, nullable=True)

    run = relationship("AgentRun", back_populates="steps")


class ChangeLog(Base):
    """Köhnə↔Yeni dəyişikliklərin auditi (müqayisə paneli və yanlış xəbərdarlıq ölçümü üçün)"""
    __tablename__ = "change_logs"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"))
    university_id = Column(Integer, ForeignKey("universities.id", ondelete="CASCADE"))
    field_name = Column(String, nullable=False)   # Dəyişən sahənin adı (məs: tuition_fee)
    old_value = Column(Text, nullable=True)        # Əvvəlki dəyər
    new_value = Column(Text, nullable=True)        # Yeni dəyər
    detected_at = Column(DateTime, default=datetime.utcnow)

    program = relationship("Program")