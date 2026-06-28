from sqlalchemy.orm import Session
from .. import models

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


def _norm(value) -> str:
    return str(value).strip() if value is not None else ""


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
                if new_val != old_val:
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
