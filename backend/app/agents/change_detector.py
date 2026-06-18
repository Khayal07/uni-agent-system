from sqlalchemy.orm import Session
from .. import models

class ChangeDetectorAgent:
    def __init__(self):
        pass

    def detect_changes(self, db: Session, university_id: int, incoming_programs: list) -> dict:
        """Bazadakı mövcud ixtisaslarla yeni gələn ixtisasları unikal kombinasiya ilə müqayisə edir"""
        
        # 1. Həmin universitetə aid bazada artıq mövcud olan bütün ixtisasları çəkirik
        existing_programs = db.query(models.Program).filter(models.Program.university_id == university_id).all()
        
        # 2. TƏHLÜKƏSİZ Sürətli axtarış lüğəti (None/NULL dəyərlərə qarşı qorunma ilə)
        existing_lookup = {}
        for p in existing_programs:
            # Əgər bazada hər hansı bir sütun səhvən NULL-dırsa, çökməsin deyə (p.sahə or "") edirik
            name = (p.program_name or "").lower().strip()
            deg = (p.degree or "").lower().strip()
            lang = (p.language or "").lower().strip()
            existing_lookup[(name, deg, lang)] = p
        
        report = {
            "new": [],        # Bazada heç olmayan tamamilə yeni ixtisaslar
            "updated": [],    # Özü var, amma qiyməti dəyişən ixtisaslar
            "unchanged_count": 0  # Hər şeyi eyni qalan ixtisasların sayı
        }
        
        # 3. Müqayisə dövrəsi
        for incoming in incoming_programs:
            raw_name = incoming.get("program_name", "")
            raw_deg = incoming.get("degree", "")
            raw_lang = incoming.get("language", "")
            
            # Gələn datanın da təhlükəsizlik formatlanması
            name = str(raw_name).lower().strip() if raw_name else ""
            deg = str(raw_deg).lower().strip() if raw_deg else ""
            lang = str(raw_lang).lower().strip() if raw_lang else ""
            
            key = (name, deg, lang)
            
            if key not in existing_lookup:
                # İxtisas bazada tapılmadı -> Deməli yenidir
                report["new"].append(incoming)
            else:
                # İxtisas bazada var, yoxlayaq görək qiyməti dəyişibmi?
                db_prog = existing_lookup[key]
                incoming_fee = str(incoming.get("tuition_fee", "0")).strip()
                db_fee = str(db_prog.tuition_fee).strip() if db_prog.tuition_fee else "0"
                
                if incoming_fee != db_fee:
                    # Qiymət dəyişibsə, mövcud DB sətirinin ID-sini ötürürük ki, SQL UPDATE edə bilsin
                    incoming["id"] = db_prog.id
                    report["updated"].append(incoming)
                else:
                    report["unchanged_count"] += 1
                    
        print(f"[Change Detector]: Analiz bitdi. Yeni: {len(report['new'])}, Yenilənən: {len(report['updated'])}, Dəyişməyən: {report['unchanged_count']}")
        return report