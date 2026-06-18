from sqlalchemy.orm import Session
from .. import models

class ChangeDetectorAgent:
    def __init__(self):
        pass

    def detect_changes(self, db: Session, university_id: int, incoming_programs: list) -> dict:
        """Bazadakı mövcud ixtisaslarla yeni gələn ixtisasları unikal kombinasiya ilə müqayisə edir"""
        
        # 1. Həmin universitetə aid bazada artıq mövcud olan bütün ixtisasları çəkirik
        existing_programs = db.query(models.Program).filter(models.Program.university_id == university_id).all()
        
        # 2. Sürətli axtarış (O(1) complexity) üçün lüğət (dict) yaradırıq. 
        # Açar olaraq unikal kombinasiya götürürük: (ad, dərəcə, tədris dili)
        existing_lookup = {
            (p.program_name.lower().strip(), p.degree.lower().strip(), p.language.lower().strip()): p 
            for p in existing_programs
        }
        
        report = {
            "new": [],        # Bazada heç olmayan tamamilə yeni ixtisaslar
            "updated": [],    # Özü var, amma qiyməti və ya digər sahəsi dəyişən ixtisaslar
            "unchanged_count": 0  # Hər şeyi eyni qalan ixtisasların sayı
        }
        
        # 3. Müqayisə dövrəsi
        for incoming in incoming_programs:
            name = incoming.get("program_name", "").lower().strip()
            deg = incoming.get("degree", "").lower().strip()
            lang = incoming.get("language", "").lower().strip()
            
            key = (name, deg, lang)
            
            if key not in existing_lookup:
                # İxtisas bazada tapılmadı -> Deməli yenidir
                report["new"].append(incoming)
            else:
                # İxtisas bazada var, yoxlayaq görək qiyməti dəyişibmi?
                db_prog = existing_lookup[key]
                incoming_fee = str(incoming.get("tuition_fee", "0"))
                db_fee = str(db_prog.tuition_fee) if db_prog.tuition_fee else "0"
                
                if incoming_fee != db_fee:
                    # Qiymət dəyişibsə, mövcud DB sətirinin ID-sini də ötürürük ki, SQL UPDATE edə bilsin
                    incoming["id"] = db_prog.id
                    report["updated"].append(incoming)
                else:
                    report["unchanged_count"] += 1
                    
        print(f"[Change Detector]: Analiz bitdi. Yeni: {len(report['new'])}, Yenilənən: {len(report['updated'])}, Dəyişməyən: {report['unchanged_count']}")
        return report