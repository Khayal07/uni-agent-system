"""UniAgent üçün vahid testlər — LLM çağırışı YOXDUR (təmiz, deterministik funksiyalar).

Validation Agent (qayda-əsaslı confidence), Change Detector (yanlış xəbərdarlıq daxil),
HTML təmizliyi, JSON parse və sahə üzrə Precision/Recall nümunəsi yoxlanılır.
"""
import os
# app.database import-dan əvvəl etibarlı bir DATABASE_URL təyin edirik (Postgres tələb olunmasın)
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app import models
from app.agents.validation import ValidationAgent
from app.agents.change_detector import ChangeDetectorAgent
from app.agents.extraction import ExtractionAgent, parse_json_block


# ----------------------------------------------------------------------
# Test üçün izolyasiya olunmuş in-memory SQLite sessiyası
# ----------------------------------------------------------------------
@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


# ----------------------------------------------------------------------
# Validation Agent
# ----------------------------------------------------------------------
def test_validation_high_confidence_when_fields_in_source():
    agent = ValidationAgent()
    prog = {
        "faculty": "Bakalavriat", "program_name": "Kompüter mühəndisliyi",
        "degree": "Bachelor", "language": "English", "tuition_fee": "5400",
        "application_deadline": "25 İyul 2026", "gpa_requirement": "300 ball",
        "documents_required": "Attestat, IELTS 5.5",
    }
    source = ("Kompüter mühəndisliyi Bachelor English 5400 AZN "
              "son müraciət 25 İyul 2026 minimum 300 ball Attestat IELTS 5.5")
    result = agent.validate_data([prog], source)
    assert len(result) == 1
    assert result[0]["confidence_score"] >= 0.75


def test_validation_low_confidence_when_unverifiable():
    agent = ValidationAgent()
    prog = {"program_name": "Naməlum ixtisas"}  # mənbədə yoxdur, sahələr boş
    result = agent.validate_data([prog], "tamamilə əlaqəsiz mətn")
    assert result[0]["confidence_score"] < 0.75


def test_validation_drops_nameless_rows():
    agent = ValidationAgent()
    progs = [{"program_name": ""}, {"program_name": "Maliyyə"}]
    result = agent.validate_data(progs, "Maliyyə 3500")
    assert len(result) == 1
    assert result[0]["program_name"] == "Maliyyə"


def test_validation_normalizes_fee():
    agent = ValidationAgent()
    prog = {"program_name": "Maliyyə", "tuition_fee": "3 500 AZN"}
    result = agent.validate_data([prog], "Maliyyə 3500")
    assert result[0]["tuition_fee"] == "3500"


def test_validation_field_confidence_is_json():
    import json
    agent = ValidationAgent()
    prog = {"program_name": "Maliyyə", "degree": "Bachelor", "tuition_fee": "3500"}
    result = agent.validate_data([prog], "Maliyyə Bachelor 3500")
    fc = json.loads(result[0]["field_confidence"])
    assert "program_name" in fc and "tuition_fee" in fc


# ----------------------------------------------------------------------
# Change Detector Agent
# ----------------------------------------------------------------------
def _seed_program(db, **kwargs):
    defaults = dict(university_id=1, program_name="Maliyyə", degree="Bachelor",
                    language="Azerbaijani", tuition_fee="3500")
    defaults.update(kwargs)
    p = models.Program(**defaults)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_change_detector_detects_new(db):
    agent = ChangeDetectorAgent()
    incoming = [{"program_name": "Data Science", "degree": "Bachelor", "tuition_fee": "4200"}]
    report = agent.detect_changes(db, university_id=1, incoming_programs=incoming)
    assert len(report["new"]) == 1
    assert len(report["updated"]) == 0


def test_change_detector_detects_updated_fee(db):
    _seed_program(db, tuition_fee="3500")
    agent = ChangeDetectorAgent()
    incoming = [{"program_name": "Maliyyə", "degree": "Bachelor",
                 "language": "Azerbaijani", "tuition_fee": "3800"}]
    report = agent.detect_changes(db, university_id=1, incoming_programs=incoming)
    assert len(report["updated"]) == 1
    assert len(report["new"]) == 0
    # ChangeLog qeydi yaranmalıdır
    db.commit()
    logs = db.query(models.ChangeLog).all()
    assert any(c.field_name == "tuition_fee" and c.new_value == "3800" for c in logs)


def test_change_detector_unchanged(db):
    _seed_program(db, tuition_fee="3500")
    agent = ChangeDetectorAgent()
    incoming = [{"program_name": "Maliyyə", "degree": "Bachelor",
                 "language": "Azerbaijani", "tuition_fee": "3500"}]
    report = agent.detect_changes(db, university_id=1, incoming_programs=incoming)
    assert report["unchanged_count"] == 1


def test_change_detector_no_false_new_on_language_change(db):
    """Dil dəyişikliyi 'yeni' yox, 'yenilənmiş' kimi qiymətləndirilməlidir (yanlış xəbərdarlıq yoxdur)."""
    _seed_program(db, language="Azerbaijani")
    agent = ChangeDetectorAgent()
    incoming = [{"program_name": "Maliyyə", "degree": "Bachelor",
                 "language": "Azerbaijani, English", "tuition_fee": "3500"}]
    report = agent.detect_changes(db, university_id=1, incoming_programs=incoming)
    assert len(report["new"]) == 0          # YANLIŞ 'yeni' xəbərdarlığı OLMAMALIDIR
    assert len(report["updated"]) == 1       # dil sahəsi dəyişib


# ----------------------------------------------------------------------
# Extraction Agent — təmiz funksiyalar
# ----------------------------------------------------------------------
def test_clean_html_strips_tags_and_scripts():
    agent = ExtractionAgent()
    html = "<html><head><style>.x{color:red}</style></head><body><script>alert(1)</script><h1>Maliyyə</h1><p>3500 AZN</p></body></html>"
    text = agent.clean_html(html)
    assert "Maliyyə" in text and "3500" in text
    assert "alert" not in text and "color:red" not in text


def test_parse_json_block_handles_fences_and_think_tags():
    raw = "<think>düşünürəm...</think>```json\n[{\"program_name\": \"Maliyyə\"}]\n```"
    data = parse_json_block(raw)
    assert isinstance(data, list) and data[0]["program_name"] == "Maliyyə"


def test_parse_json_block_returns_none_on_garbage():
    assert parse_json_block("heç bir json yoxdur") is None


# ----------------------------------------------------------------------
# Sahə üzrə Precision / Recall nümunəsi (qiymətləndirmə metrikası)
# ----------------------------------------------------------------------
def _precision_recall(gold: set, predicted: set):
    tp = len(gold & predicted)
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(gold) if gold else 0.0
    return precision, recall


def test_program_name_precision_recall():
    gold = {"Maliyyə", "Marketinq", "Mühasibat"}
    predicted = {"Maliyyə", "Marketinq", "Beynəlxalq ticarət"}  # 1 səhv, 1 əskik
    precision, recall = _precision_recall(gold, predicted)
    assert round(precision, 2) == 0.67   # 2/3 düzgün proqnoz
    assert round(recall, 2) == 0.67      # 3-dən 2-si tapıldı
