import re
import json

# Tanınan dillər (language sahəsinin format yoxlaması üçün)
KNOWN_LANGUAGES = [
    "azerbaijani", "azerbaycan", "azərbaycan", "az",
    "english", "eng", "ingilis", "en",
    "russian", "rus", "rusca", "ru",
    "turkish", "turk", "türk", "tr",
]

# Tarix formatını tanımaq üçün ay adları (AZ + EN) və ümumi tarix şablonları
MONTHS = [
    "yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust",
    "sentyabr", "oktyabr", "noyabr", "dekabr",
    "january", "february", "march", "april", "june", "july", "august",
    "september", "october", "november", "december",
]
DATE_NUMERIC = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b")
YEAR = re.compile(r"\b(20\d{2})\b")


def _norm(value) -> str:
    """Dəyəri normalize edir: kiçik hərf, artıq boşluqları yığır."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).lower()).strip()


def _source_contains(value: str, source_norm: str) -> bool:
    """Çıxarılmış dəyərin mənbə mətnində tapılıb-tapılmadığını yoxlayır."""
    v = _norm(value)
    if not v or not source_norm:
        return False
    # Tam alt-sətir uyğunluğu
    if v in source_norm:
        return True
    # Token əsaslı uyğunluq: mənalı sözlərin (uzunluq > 3) əksəriyyəti mətndədirsə
    tokens = [t for t in re.findall(r"[a-zəçğışöü0-9]+", v) if len(t) > 3]
    if not tokens:
        return False
    hits = sum(1 for t in tokens if t in source_norm)
    return hits >= max(1, len(tokens) // 2 + len(tokens) % 2)


def _fee_in_source(fee_digits: str, source_norm: str) -> bool:
    """Təhsil haqqı rəqəminin mənbədə görünüb-görünmədiyini yoxlayır (boşluqlu yazılışa dözümlü)."""
    if not fee_digits:
        return False
    if fee_digits in source_norm:
        return True
    # Mənbədəki rəqəmlərin arasındakı boşluq/nöqtələri təmizləyib axtarırıq ("2 400" -> "2400")
    collapsed = re.sub(r"[ .,]", "", source_norm)
    return fee_digits in collapsed


def _field_score(present: bool, format_ok: bool, source_ok: bool) -> float:
    """Sahə üçün etibarlılıq balı: mövcudluq + format + mənbə uyğunluğu."""
    if not present:
        return 0.0
    score = 0.30  # mövcuddur (baza)
    if format_ok:
        score += 0.35
    if source_ok:
        score += 0.35
    return round(min(score, 1.0), 2)


class ValidationAgent:
    """Çıxarılmış məlumatı səhifə mətni ilə müqayisə edir, format yoxlaması aparır
    və hər sahə üçün qayda-əsaslı (deterministik) etibarlılıq balı hesablayır."""

    # Ümumi confidence hesablamasında sahə çəkiləri
    WEIGHTS = {
        "program_name": 0.30,
        "tuition_fee": 0.20,
        "degree": 0.15,
        "language": 0.10,
        "application_deadline": 0.10,
        "gpa_requirement": 0.075,
        "documents_required": 0.075,
    }

    def __init__(self):
        pass

    def validate_data(self, extracted_programs: list, source_text: str = "") -> list:
        """Məlumatları yoxlayıb normallaşdırır və hər sətrə confidence_score əlavə edir.

        source_text — səhifədən çıxarılmış təmiz mətn; sahələrin doğrulanması üçün."""
        source_norm = _norm(source_text)
        valid_programs = []

        for prog in extracted_programs:
            program_name = prog.get("program_name")

            # Əsas təməl sütun boşdursa, bu sətri bazaya yazmırıq
            if not program_name or str(program_name).strip() == "":
                print(f"[Validation Agent]: Adsız ixtisas aşkarlandı və silindi -> {prog}")
                continue

            # --- Normalizasiya ---
            # Qiymət: yalnız rəqəmlər
            fee_raw = str(prog.get("tuition_fee", "") or "")
            cleaned_fee = "".join(ch for ch in fee_raw if ch.isdigit())
            prog["tuition_fee"] = cleaned_fee if cleaned_fee else "0"

            # Dərəcə standartlaşdırması
            if prog.get("degree") not in ["Bachelor", "Master", "PhD"]:
                prog["degree"] = "Bachelor"

            # Default faculty
            if not prog.get("faculty"):
                prog["faculty"] = "Bakalavriat"

            # --- Sahə-səviyyə etibarlılıq balları ---
            scores = {}

            # program_name: format = ən azı 2 simvol
            scores["program_name"] = _field_score(
                present=True,
                format_ok=len(_norm(program_name)) >= 2,
                source_ok=_source_contains(program_name, source_norm),
            )

            # tuition_fee
            fee = prog["tuition_fee"]
            fee_present = fee_raw.strip() != ""
            scores["tuition_fee"] = _field_score(
                present=fee_present,
                format_ok=fee.isdigit(),
                source_ok=_fee_in_source(fee, source_norm) or fee == "0",
            )

            # degree
            deg = prog.get("degree")
            scores["degree"] = _field_score(
                present=bool(deg),
                format_ok=deg in ["Bachelor", "Master", "PhD"],
                source_ok=_source_contains(deg, source_norm),
            )

            # language
            lang = prog.get("language")
            lang_norm = _norm(lang)
            scores["language"] = _field_score(
                present=bool(lang_norm),
                format_ok=any(k in lang_norm for k in KNOWN_LANGUAGES),
                source_ok=_source_contains(lang, source_norm),
            )

            # application_deadline
            dl = prog.get("application_deadline")
            dl_norm = _norm(dl)
            dl_format = bool(
                dl_norm
                and (
                    DATE_NUMERIC.search(dl_norm)
                    or YEAR.search(dl_norm)
                    or any(m in dl_norm for m in MONTHS)
                )
            )
            scores["application_deadline"] = _field_score(
                present=bool(dl_norm),
                format_ok=dl_format,
                source_ok=_source_contains(dl, source_norm),
            )

            # gpa_requirement
            gpa = prog.get("gpa_requirement")
            gpa_norm = _norm(gpa)
            scores["gpa_requirement"] = _field_score(
                present=bool(gpa_norm),
                format_ok=bool(re.search(r"\d", gpa_norm)),
                source_ok=_source_contains(gpa, source_norm),
            )

            # documents_required
            docs = prog.get("documents_required")
            docs_norm = _norm(docs)
            scores["documents_required"] = _field_score(
                present=bool(docs_norm),
                format_ok=len(docs_norm) >= 3,
                source_ok=_source_contains(docs, source_norm),
            )

            # --- Ümumi confidence (çəkili orta) ---
            total_w = sum(self.WEIGHTS.values())
            confidence = sum(self.WEIGHTS[f] * scores[f] for f in self.WEIGHTS) / total_w

            prog["confidence_score"] = round(confidence, 3)
            prog["field_confidence"] = json.dumps(scores, ensure_ascii=False)

            valid_programs.append(prog)

        avg = (
            round(sum(p["confidence_score"] for p in valid_programs) / len(valid_programs), 3)
            if valid_programs
            else 0
        )
        print(
            f"[Validation Agent]: Yoxlama tamamlandı. "
            f"{len(valid_programs)}/{len(extracted_programs)} ixtisas keçdi. Orta etibarlılıq: {avg}"
        )
        return valid_programs
