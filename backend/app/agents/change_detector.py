import re
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from .. import models
from ..config import SEMANTIC_SIMILARITY_THRESHOLD

# Dəyişiklik üçün izlənən sahələr (incoming dict açarı == model atributu)
TRACKED_FIELDS = [
    "tuition_fee",
    "language",
    "application_deadline",
    "gpa_requirement",
    "documents_required",
    "requirements",
    "faculty",
]

# Uzun/sərbəst mətn sahələri — burada kiçik format fərqi dəyişiklik sayılmamalıdır.
# Dəqiq sahələr (qiymət, tarix, GPA, dil) exact müqayisə ilə qalır.
SEMANTIC_FIELDS = {"documents_required", "requirements"}


def _norm(value) -> str:
    return str(value).strip() if value is not None else ""


def _semantic_norm(text: str) -> str:
    """Semantic müqayisə üçün dərin normalizasiya: kiçik hərf, durğu işarələrini at,
    boşluqları yığ, tokenləri əlifba sırası ilə düz (sıralama fərqinə həssas olmasın)."""
    t = re.sub(r"[^\wəçğışöü ]+", " ", str(text).lower(), flags=re.UNICODE)
    tokens = sorted(w for w in t.split() if w)
    return " ".join(tokens)


def _semantic_equal(old: str, new: str, threshold: float = SEMANTIC_SIMILARITY_THRESHOLD) -> bool:
    """İki mətnin mənaca eyni sayıla biləcəyini deterministik oxşarlıqla yoxlayır.

    Token-Jaccard və difflib nisbətinin maksimumu həddi keçirsə, eyni sayılır
    (yəni yalnız formatlaşma/sıralama/durğu fərqidir — əsl dəyişiklik deyil)."""
    on, nn = _semantic_norm(old), _semantic_norm(new)
    if on == nn:
        return True
    if not on or not nn:
        return False
    a, b = set(on.split()), set(nn.split())
    jaccard = len(a & b) / len(a | b) if (a | b) else 0.0
    ratio = SequenceMatcher(None, on, nn).ratio()
    return max(jaccard, ratio) >= threshold


def _field_unchanged(field: str, old_val: str, new_val: str) -> bool:
    """Sahə üçün 'dəyişməyib' qərarı: semantic sahələrdə oxşarlıq, digərlərində exact."""
    if old_val == new_val:
        return True
    if field in SEMANTIC_FIELDS:
        return _semantic_equal(old_val, new_val)
    return False


class ChangeDetectorAgent:
    def __init__(self):
        pass

    def detect_changes(self, db: Session, university_id: int, incoming_programs: list) -> dict:
        """Bazadakı mövcud ixtisaslarla yeni gələnləri (ad, dərəcə) açarı ilə müqayisə edir.

        Dil variasiyasından doğan yanlış 'yeni' xəbərdarlığının qarşısını almaq üçün
        unikal açar yalnız (program_name, degree)-dir; dil isə izlənən bir sahədir.
        Dəyişən hər sahə üçün ChangeLog qeydi yaradılır (köhnə → yeni audit)."""

        existing_programs = (
            db.query(models.Program)
            .filter(models.Program.university_id == university_id)
            .all()
        )

        # None/NULL dəyərlərə qarşı qorunma ilə sürətli axtarış lüğəti
        existing_lookup = {}
        for p in existing_programs:
            name = (p.program_name or "").lower().strip()
            deg = (p.degree or "").lower().strip()
            existing_lookup[(name, deg)] = p

        report = {
            "new": [],            # Bazada heç olmayan tamamilə yeni ixtisaslar
            "updated": [],        # Mövcud, amma hər hansı sahəsi dəyişən ixtisaslar
            "unchanged_count": 0, # Hər şeyi eyni qalan ixtisasların sayı
        }

        for incoming in incoming_programs:
            name = _norm(incoming.get("program_name")).lower()
            deg = _norm(incoming.get("degree")).lower()
            key = (name, deg)

            if key not in existing_lookup:
                report["new"].append(incoming)
                continue

            db_prog = existing_lookup[key]

            # İzlənən sahələri tək-tək müqayisə edirik
            changed_fields = []
            for field in TRACKED_FIELDS:
                old_val = _norm(getattr(db_prog, field, None))
                new_val = _norm(incoming.get(field))
                # Semantic sahələrdə yalnız-format fərqi dəyişiklik sayılmır
                if not _field_unchanged(field, old_val, new_val):
                    changed_fields.append({"field": field, "old": old_val, "new": new_val})
                    # Köhnə → yeni dəyişikliyi audit jurnalına yazırıq
                    db.add(
                        models.ChangeLog(
                            program_id=db_prog.id,
                            university_id=university_id,
                            field_name=field,
                            old_value=old_val,
                            new_value=new_val,
                        )
                    )

            if changed_fields:
                incoming["id"] = db_prog.id
                incoming["changed_fields"] = changed_fields
                report["updated"].append(incoming)
            else:
                report["unchanged_count"] += 1

        print(
            f"[Change Detector]: Analiz bitdi. Yeni: {len(report['new'])}, "
            f"Yenilənən: {len(report['updated'])}, Dəyişməyən: {report['unchanged_count']}"
        )
        return report
