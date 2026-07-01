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


def test_semantic_equal_ignores_formatting():
    from app.agents.change_detector import _semantic_equal
    # Yalnız durğu/sıralama/böyük-kiçik fərqi — eyni sayılmalı
    assert _semantic_equal("Attestat, şəxsiyyət vəsiqəsi", "şəxsiyyət vəsiqəsi Attestat")
    assert _semantic_equal("IELTS 5.5; Attestat", "ielts 5.5 attestat")


def test_semantic_equal_detects_real_difference():
    from app.agents.change_detector import _semantic_equal
    assert not _semantic_equal("Attestat, IELTS 5.5", "Attestat, IELTS 7.0, motivasiya məktubu")


def test_change_detector_semantic_docs_not_flagged(db):
    """Sənədlər sahəsində yalnız format/sıralama fərqi 'dəyişiklik' sayılmamalıdır."""
    _seed_program(db, documents_required="Attestat, şəxsiyyət vəsiqəsi, foto")
    agent = ChangeDetectorAgent()
    incoming = [{"program_name": "Maliyyə", "degree": "Bachelor", "language": "Azerbaijani",
                 "tuition_fee": "3500", "documents_required": "foto şəxsiyyət vəsiqəsi Attestat"}]
    report = agent.detect_changes(db, university_id=1, incoming_programs=incoming)
    assert report["unchanged_count"] == 1
    assert len(report["updated"]) == 0


def test_change_detector_semantic_docs_real_change_flagged(db):
    _seed_program(db, documents_required="Attestat, foto")
    agent = ChangeDetectorAgent()
    incoming = [{"program_name": "Maliyyə", "degree": "Bachelor", "language": "Azerbaijani",
                 "tuition_fee": "3500", "documents_required": "Attestat, foto, IELTS 6.5, motivasiya məktubu"}]
    report = agent.detect_changes(db, university_id=1, incoming_programs=incoming)
    assert len(report["updated"]) == 1


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


def test_reviewer_rejects_meta_reasoning():
    from app.agents.reviewer import ReviewerAgent
    agent = ReviewerAgent()
    # Modelin "düşüncə" mətni (screenshot-dakı kimi) → təmizləyici boş qaytarmalı
    meta = ("We need to produce a professional high-level executive summary in Azerbaijani, "
            "with approval tag. Must be concise 3-4 sentences. The metrics: ...")
    assert agent._clean_summary(meta) == ""


def test_reviewer_keeps_clean_summary():
    from app.agents.reviewer import ReviewerAgent
    agent = ReviewerAgent()
    good = "[TƏSDİQLƏNDİ] Kent üzrə analiz tamamlandı: 5 yeni ixtisas bazaya inteqrasiya edildi."
    assert agent._clean_summary(good).startswith("[TƏSDİQLƏNDİ]")


def test_reviewer_strips_think_block():
    from app.agents.reviewer import ReviewerAgent
    agent = ReviewerAgent()
    raw = "<think>plan qururam...</think>[TƏSDİQLƏNDİ] Analiz bitdi, 3 yeni ixtisas əlavə olundu."
    out = agent._clean_summary(raw)
    assert "think" not in out and out.startswith("[TƏSDİQLƏNDİ]")


def test_reviewer_fallback_mentions_changes():
    from app.agents.reviewer import ReviewerAgent
    agent = ReviewerAgent()
    report = {"new": [1, 2], "updated": [3], "unchanged_count": 4}
    out = agent._fallback_summary("Kent", report, 0.58, 6)
    assert out.startswith("[TƏSDİQLƏNDİ]")
    assert "2 yeni" in out and "1 yenilənmiş" in out and "6 qeyd" in out


def test_clean_html_drops_nav_and_footer():
    agent = ExtractionAgent()
    html = ("<body><nav>Ana səhifə Əlaqə Menyu</nav>"
            "<main><h1>Maliyyə</h1><p>3500 AZN</p></main>"
            "<footer>Bütün hüquqlar qorunur 2026</footer></body>")
    text = agent.clean_html(html)
    assert "Maliyyə" in text and "3500" in text
    assert "Menyu" not in text and "hüquqlar" not in text


def test_clean_html_falls_back_when_main_too_small():
    """<main> çox qısadırsa, tam body götürülməlidir (məzmun itməsin)."""
    agent = ExtractionAgent()
    body_text = "Maliyyə " * 100  # böyük məzmun body-də
    html = f"<body><main>qısa</main><section>{body_text}</section></body>"
    text = agent.clean_html(html)
    assert text.count("Maliyyə") >= 50


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


# ----------------------------------------------------------------------
# Crawler — heuristik link ranking + sitemap parse (LLM YOX)
# ----------------------------------------------------------------------
from app.agents.crawler import rank_candidate_urls, _parse_sitemap_xml


def test_rank_prioritizes_program_keywords():
    hrefs = [
        "https://uni.edu/contact",
        "https://uni.edu/undergraduate/programs",
        "https://uni.edu/news",
    ]
    ranked = rank_candidate_urls(hrefs, [], "https://uni.edu")
    assert ranked[0] == "https://uni.edu/undergraduate/programs"


def test_rank_filters_external_and_files():
    hrefs = [
        "https://other.com/programs",      # xarici domen
        "https://uni.edu/file.pdf",        # fayl
        "https://uni.edu/bachelor",        # keçərli
    ]
    ranked = rank_candidate_urls(hrefs, [], "https://uni.edu")
    assert ranked == ["https://uni.edu/bachelor"]


def test_rank_merges_sitemap_and_caps_top5():
    hrefs = [f"https://uni.edu/p{i}/admission" for i in range(10)]
    ranked = rank_candidate_urls(hrefs, ["https://uni.edu/study/programs"], "https://uni.edu")
    assert len(ranked) <= 5
    assert "https://uni.edu/study/programs" in ranked


def test_parse_sitemap_extracts_locs():
    xml = """<urlset><url><loc>https://uni.edu/a</loc></url>
             <url><loc>https://uni.edu/b</loc></url></urlset>"""
    assert _parse_sitemap_xml(xml) == ["https://uni.edu/a", "https://uni.edu/b"]


# ----------------------------------------------------------------------
# Crawler — anti-bot: UA rotasiyası + blok aşkarlama
# ----------------------------------------------------------------------
from app.agents.crawler import _looks_blocked, _pick_ua, USER_AGENTS


def test_looks_blocked_detects_captcha_page():
    assert _looks_blocked("<html><body>Please verify you are human. Captcha</body></html>")
    assert _looks_blocked("Access denied — request blocked by Cloudflare")


def test_looks_blocked_ignores_real_content():
    real = "Maliyyə ixtisası " * 400  # uzun, real məzmun (blok açar sözü yox)
    assert not _looks_blocked(real)
    assert not _looks_blocked("")


def test_pick_ua_rotates():
    uas = {_pick_ua(i) for i in range(len(USER_AGENTS))}
    assert len(uas) == len(USER_AGENTS)      # hər cəhddə fərqli UA
    assert _pick_ua(0) == _pick_ua(len(USER_AGENTS))  # dövri


# ----------------------------------------------------------------------
# Extraction — chunk + dedupe (15000 kəsimi əvəzinə)
# ----------------------------------------------------------------------
from app.agents.extraction import ExtractionAgent


def test_chunk_text_covers_long_text_with_overlap():
    agent = ExtractionAgent()
    text = "x" * 25000
    chunks = agent._chunk_text(text, size=12000, overlap=500)
    assert len(chunks) >= 3
    assert all(len(c) <= 12000 for c in chunks)
    # Birinci chunk-ın sonu ikincinin əvvəlində görünür (overlap)
    assert chunks[0][-100:] in chunks[1]


def test_extract_chunk_retries_once_on_failure(monkeypatch):
    """İlk cəhd uğursuz (parse olunmayan), ikinci cəhd uğurlu — retry işləməlidir."""
    agent = ExtractionAgent()
    agent.api_key = "test-key"
    calls = {"n": 0}

    class FakeResp:
        def __init__(self, content, status=200):
            self._c = content; self.status_code = status
        def json(self):
            return {"choices": [{"message": {"content": self._c}}]}

    def fake_post(url, json=None, headers=None, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeResp("zibil cavab, json yoxdur")          # parse alınmır
        return FakeResp('[{"program_name": "Maliyyə"}]')          # ikinci cəhd OK

    monkeypatch.setattr("app.agents.extraction.requests.post", fake_post)
    out = agent._extract_chunk("mətn")
    assert calls["n"] == 2                       # bir dəfə retry olundu
    assert out and out[0]["program_name"] == "Maliyyə"


def test_extract_chunk_no_infinite_retry(monkeypatch):
    """Həmişə uğursuzdursa, yalnız 2 cəhd (1 + 1 retry) olmalıdır."""
    agent = ExtractionAgent()
    agent.api_key = "test-key"
    calls = {"n": 0}

    def fake_post(url, json=None, headers=None, timeout=None):
        calls["n"] += 1
        raise RuntimeError("şəbəkə xətası")

    monkeypatch.setattr("app.agents.extraction.requests.post", fake_post)
    out = agent._extract_chunk("mətn")
    assert calls["n"] == 2 and out == []


def test_dedupe_removes_same_program_name():
    agent = ExtractionAgent()
    progs = [
        {"program_name": "Maliyyə", "tuition_fee": "2600"},
        {"program_name": " maliyyə ", "tuition_fee": "2600"},  # eyni ad, fərqli yazılış
        {"program_name": "Kompüter mühəndisliyi", "tuition_fee": "5400"},
    ]
    out = agent._dedupe(progs)
    assert len(out) == 2


# ----------------------------------------------------------------------
# Versiyalama (ProgramVersion) + audit helper-ləri
# ----------------------------------------------------------------------
from app import crud


def test_content_hash_stable_and_field_sensitive():
    p1 = {"program_name": "Maliyyə", "tuition_fee": "3500", "degree": "Bachelor"}
    p2 = {"program_name": "Maliyyə", "tuition_fee": "3500", "degree": "Bachelor"}
    p3 = {"program_name": "Maliyyə", "tuition_fee": "3800", "degree": "Bachelor"}  # fee dəyişib
    assert crud.compute_content_hash(p1) == crud.compute_content_hash(p2)
    assert crud.compute_content_hash(p1) != crud.compute_content_hash(p3)


def test_record_version_creates_v1(db):
    p = _seed_program(db, tuition_fee="3500")
    v = crud.record_version(db, p, source_url="https://uni.edu/programs")
    db.commit()
    assert v.version_no == 1 and v.is_current is True and v.valid_to is None
    assert p.current_version_id == v.id and p.content_hash == v.content_hash
    assert v.source_url == "https://uni.edu/programs"


def test_record_version_closes_previous_and_increments(db):
    p = _seed_program(db, tuition_fee="3500")
    crud.record_version(db, p)          # v1
    db.commit()
    p.tuition_fee = "3800"              # dəyişiklik
    v2 = crud.record_version(db, p)     # v2
    db.commit()

    versions = db.query(models.ProgramVersion).filter(
        models.ProgramVersion.program_id == p.id
    ).order_by(models.ProgramVersion.version_no).all()
    assert len(versions) == 2
    assert versions[0].is_current is False and versions[0].valid_to is not None
    assert versions[1].is_current is True and versions[1].version_no == 2
    assert p.current_version_id == v2.id


def test_agent_run_and_step_lifecycle(db):
    run = crud.start_run(db, university_id=1, run_type="live")
    assert run.status == "running"
    step = crud.start_step(db, run.id, "extraction", input_summary="html len=1000")
    crud.finish_step(db, step, status="done", output_summary="5 programs")
    crud.finish_run(db, run, status="success", metrics={"total": 5})

    assert step.status == "done" and step.duration_ms is not None
    assert run.status == "success" and run.finished_at is not None
    assert run.metrics_json == {"total": 5}
