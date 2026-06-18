class ValidationAgent:
    def __init__(self):
        pass

    def validate_data(self, extracted_programs: list) -> list:
        """Məlumatların tamlığını və doğruluğunu yoxlayıb süzgəcdən keçirir"""
        valid_programs = []
        
        for prog in extracted_programs:
            program_name = prog.get("program_name")
            degree = prog.get("degree")
            
            # Əgər əsas təməl sütunlar boşdursa, bu sətri bazaya yazmırıq
            if not program_name or str(program_name).strip() == "":
                print(f"[Validation Agent]: Adsız ixtisas aşkarlandı və silindi -> {prog}")
                continue
            
            # Qiymət normalizasiyası (Yalnız rəqəmləri saxlayırıq)
            fee = str(prog.get("tuition_fee", "0"))
            cleaned_fee = "".join([char for char in fee if char.isdigit()])
            prog["tuition_fee"] = cleaned_fee if cleaned_fee else "0"
            
            # Dərəcə formatını standartlaşdırırıq
            if degree not in ["Bachelor", "Master"]:
                prog["degree"] = "Bachelor"
                
            # Default faculty dəyəri
            if not prog.get("faculty"):
                prog["faculty"] = "Bakalavriat"
                
            valid_programs.append(prog)
            
        print(f"[Validation Agent]: Yoxlama tamamlandı. {len(valid_programs)}/{len(extracted_programs)} ixtisas təsdiq möhürü aldı.")
        return valid_programs