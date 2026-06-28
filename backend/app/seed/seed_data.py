"""Təkrarlana bilən demo/test üçün saxlanmış fixture datası.

Canlı skrap OpenRouter API açarından və saytların strukturundan asılıdır; bu fixture-lar
isə həmişə işləyən demo, dolu dashboard və dəyişiklik aşkarlama nümayişi təmin edir.

- SEED_UNIVERSITIES: ilkin "v1" vəziyyət (6 universitet, 30+ proqram).
- UPDATES: sonrakı bir "skrap"ı təqlid edən dəyişikliklər (qiymət dəyişir, yeni
  ixtisas əlavə olunur) — change detection + insan yoxlaması axınını offline göstərmək üçün.
"""

SEED_UNIVERSITIES = [
    {
        "name": "UNEC (Azərbaycan Dövlət İqtisad Universiteti)",
        "website_url": "https://unec.edu.az",
        "programs": [
            {"faculty": "Rəqəmsal İqtisadiyyat", "program_name": "Maliyyə", "degree": "Bachelor", "language": "Azerbaijani", "tuition_fee": "3500", "application_deadline": "15 İyul 2026", "gpa_requirement": "250 ball", "documents_required": "Attestat, şəxsiyyət vəsiqəsi, foto", "requirements": None},
            {"faculty": "Rəqəmsal İqtisadiyyat", "program_name": "Mühasibat və audit", "degree": "Bachelor", "language": "Azerbaijani", "tuition_fee": "3300", "application_deadline": "15 İyul 2026", "gpa_requirement": "240 ball", "documents_required": "Attestat, şəxsiyyət vəsiqəsi", "requirements": None},
            {"faculty": "İqtisadiyyat", "program_name": "Beynəlxalq ticarət", "degree": "Bachelor", "language": "English", "tuition_fee": "4000", "application_deadline": "15 İyul 2026", "gpa_requirement": "300 ball", "documents_required": "Attestat, IELTS 5.5", "requirements": None},
            {"faculty": "İqtisadiyyat", "program_name": "Marketinq", "degree": "Bachelor", "language": "Azerbaijani", "tuition_fee": "3200", "application_deadline": "15 İyul 2026", "gpa_requirement": "230 ball", "documents_required": "Attestat", "requirements": None},
            {"faculty": "Magistratura", "program_name": "Maliyyə menecmenti", "degree": "Master", "language": "Azerbaijani", "tuition_fee": "4500", "application_deadline": "20 Avqust 2026", "gpa_requirement": "GPA 3.0", "documents_required": "Bakalavr diplomu, foto", "requirements": None},
        ],
    },
    {
        "name": "ADA University",
        "website_url": "https://ada.edu.az",
        "programs": [
            {"faculty": "School of IT and Engineering", "program_name": "Computer Science", "degree": "Bachelor", "language": "English", "tuition_fee": "9500", "application_deadline": "30 İyun 2026", "gpa_requirement": "GPA 3.0", "documents_required": "Transcript, SAT, IELTS 6.0", "requirements": None},
            {"faculty": "School of IT and Engineering", "program_name": "Computer Engineering", "degree": "Bachelor", "language": "English", "tuition_fee": "9500", "application_deadline": "30 İyun 2026", "gpa_requirement": "GPA 3.0", "documents_required": "Transcript, SAT, IELTS 6.0", "requirements": None},
            {"faculty": "School of Business", "program_name": "Business Administration", "degree": "Bachelor", "language": "English", "tuition_fee": "8800", "application_deadline": "30 İyun 2026", "gpa_requirement": "GPA 2.75", "documents_required": "Transcript, IELTS 6.0", "requirements": None},
            {"faculty": "School of Public and International Affairs", "program_name": "International Studies", "degree": "Bachelor", "language": "English", "tuition_fee": "8500", "application_deadline": "30 İyun 2026", "gpa_requirement": "GPA 2.75", "documents_required": "Transcript, IELTS 6.0", "requirements": None},
            {"faculty": "Graduate", "program_name": "MBA", "degree": "Master", "language": "English", "tuition_fee": "12000", "application_deadline": "10 Avqust 2026", "gpa_requirement": "GPA 3.0, GMAT", "documents_required": "Bachelor diploma, CV, IELTS 6.5", "requirements": None},
        ],
    },
    {
        "name": "Bakı Dövlət Universiteti (BDU)",
        "website_url": "https://bsu.edu.az",
        "programs": [
            {"faculty": "Tətbiqi riyaziyyat və kibernetika", "program_name": "Kompüter elmləri", "degree": "Bachelor", "language": "Azerbaijani", "tuition_fee": "2700", "application_deadline": "12 İyul 2026", "gpa_requirement": "350 ball", "documents_required": "Attestat, şəxsiyyət vəsiqəsi", "requirements": None},
            {"faculty": "Fizika", "program_name": "Fizika", "degree": "Bachelor", "language": "Azerbaijani", "tuition_fee": "2200", "application_deadline": "12 İyul 2026", "gpa_requirement": "300 ball", "documents_required": "Attestat", "requirements": None},
            {"faculty": "Kimya", "program_name": "Kimya", "degree": "Bachelor", "language": "Azerbaijani", "tuition_fee": "2200", "application_deadline": "12 İyul 2026", "gpa_requirement": "280 ball", "documents_required": "Attestat", "requirements": None},
            {"faculty": "Hüquq", "program_name": "Hüquqşünaslıq", "degree": "Bachelor", "language": "Azerbaijani", "tuition_fee": "3000", "application_deadline": "12 İyul 2026", "gpa_requirement": "400 ball", "documents_required": "Attestat, şəxsiyyət vəsiqəsi, foto", "requirements": None},
            {"faculty": "Beynəlxalq münasibətlər", "program_name": "Beynəlxalq münasibətlər", "degree": "Bachelor", "language": "English", "tuition_fee": "3500", "application_deadline": "12 İyul 2026", "gpa_requirement": "420 ball", "documents_required": "Attestat, IELTS 5.5", "requirements": None},
        ],
    },
    {
        "name": "Xəzər Universiteti",
        "website_url": "https://khazar.org",
        "programs": [
            {"faculty": "Mühəndislik və tətbiqi elmlər", "program_name": "Kompüter mühəndisliyi", "degree": "Bachelor", "language": "English", "tuition_fee": "5400", "application_deadline": "25 İyul 2026", "gpa_requirement": "300 ball", "documents_required": "Attestat, IELTS 5.5", "requirements": None},
            {"faculty": "Mühəndislik və tətbiqi elmlər", "program_name": "Süni intellekt", "degree": "Bachelor", "language": "English", "tuition_fee": "5600", "application_deadline": "25 İyul 2026", "gpa_requirement": "320 ball", "documents_required": "Attestat, IELTS 5.5", "requirements": None},
            {"faculty": "İqtisadiyyat və menecment", "program_name": "Maliyyə", "degree": "Bachelor", "language": "Azerbaijani", "tuition_fee": "4800", "application_deadline": "25 İyul 2026", "gpa_requirement": "260 ball", "documents_required": "Attestat", "requirements": None},
            {"faculty": "Humanitar elmlər", "program_name": "İngilis dili və ədəbiyyatı", "degree": "Bachelor", "language": "English", "tuition_fee": "4500", "application_deadline": "25 İyul 2026", "gpa_requirement": "250 ball", "documents_required": "Attestat, IELTS 6.0", "requirements": None},
            {"faculty": "İqtisadiyyat və menecment", "program_name": "Biznesin idarə edilməsi", "degree": "Bachelor", "language": "Azerbaijani", "tuition_fee": "4600", "application_deadline": "25 İyul 2026", "gpa_requirement": "240 ball", "documents_required": "Attestat", "requirements": None},
        ],
    },
    {
        "name": "Azərbaycan Texniki Universiteti (AzTU)",
        "website_url": "https://aztu.edu.az",
        "programs": [
            {"faculty": "İnformasiya texnologiyaları", "program_name": "İnformasiya texnologiyaları", "degree": "Bachelor", "language": "Azerbaijani", "tuition_fee": "2400", "application_deadline": "14 İyul 2026", "gpa_requirement": "230 ball", "documents_required": "Attestat, şəxsiyyət vəsiqəsi", "requirements": None},
            {"faculty": "Maşınqayırma", "program_name": "Mexatronika və robototexnika", "degree": "Bachelor", "language": "Azerbaijani", "tuition_fee": "2300", "application_deadline": "14 İyul 2026", "gpa_requirement": "220 ball", "documents_required": "Attestat", "requirements": None},
            {"faculty": "Energetika", "program_name": "Elektroenergetika mühəndisliyi", "degree": "Bachelor", "language": "Azerbaijani", "tuition_fee": "2300", "application_deadline": "14 İyul 2026", "gpa_requirement": "210 ball", "documents_required": "Attestat", "requirements": None},
            {"faculty": "Nəqliyyat", "program_name": "Nəqliyyat mühəndisliyi", "degree": "Bachelor", "language": "Azerbaijani", "tuition_fee": "2200", "application_deadline": "14 İyul 2026", "gpa_requirement": "200 ball", "documents_required": "Attestat", "requirements": None},
            {"faculty": "İnformasiya texnologiyaları", "program_name": "Kompüter mühəndisliyi", "degree": "Bachelor", "language": "Azerbaijani", "tuition_fee": "2500", "application_deadline": "14 İyul 2026", "gpa_requirement": "250 ball", "documents_required": "Attestat, şəxsiyyət vəsiqəsi", "requirements": None},
        ],
    },
    {
        "name": "Baku Higher Oil School (BHOS)",
        "website_url": "https://bhos.edu.az",
        "programs": [
            {"faculty": "Process Automation Engineering", "program_name": "Process Automation Engineering", "degree": "Bachelor", "language": "English", "tuition_fee": "6000", "application_deadline": "5 İyul 2026", "gpa_requirement": "500 ball", "documents_required": "Attestat, IELTS 5.5", "requirements": None},
            {"faculty": "Chemical Engineering", "program_name": "Chemical Engineering", "degree": "Bachelor", "language": "English", "tuition_fee": "6000", "application_deadline": "5 İyul 2026", "gpa_requirement": "500 ball", "documents_required": "Attestat, IELTS 5.5", "requirements": None},
            {"faculty": "Petroleum Engineering", "program_name": "Petroleum Engineering", "degree": "Bachelor", "language": "English", "tuition_fee": "6500", "application_deadline": "5 İyul 2026", "gpa_requirement": "550 ball", "documents_required": "Attestat, IELTS 6.0", "requirements": None},
            {"faculty": "IT and Computer Engineering", "program_name": "Computer Engineering", "degree": "Bachelor", "language": "English", "tuition_fee": "6200", "application_deadline": "5 İyul 2026", "gpa_requirement": "520 ball", "documents_required": "Attestat, IELTS 5.5", "requirements": None},
            {"faculty": "Mechanical Engineering", "program_name": "Mechanical Engineering", "degree": "Bachelor", "language": "English", "tuition_fee": "6000", "application_deadline": "5 İyul 2026", "gpa_requirement": "500 ball", "documents_required": "Attestat, IELTS 5.5", "requirements": None},
        ],
    },
]


# Sonrakı bir "skrap"ı təqlid edən dəyişikliklər (universitet adına görə açar).
# Change detection nümayişi: mövcud ixtisasın qiyməti/son tarixi dəyişir + 1 yeni ixtisas.
UPDATES = {
    "UNEC (Azərbaycan Dövlət İqtisad Universiteti)": [
        # Mövcud ixtisas — təhsil haqqı 3500 -> 3800 (UPDATED gözlənilir)
        {"faculty": "Rəqəmsal İqtisadiyyat", "program_name": "Maliyyə", "degree": "Bachelor", "language": "Azerbaijani", "tuition_fee": "3800", "application_deadline": "15 İyul 2026", "gpa_requirement": "250 ball", "documents_required": "Attestat, şəxsiyyət vəsiqəsi, foto", "requirements": None},
        # Tamamilə yeni ixtisas (NEW gözlənilir)
        {"faculty": "Rəqəmsal İqtisadiyyat", "program_name": "Data Science", "degree": "Bachelor", "language": "English", "tuition_fee": "4200", "application_deadline": "15 İyul 2026", "gpa_requirement": "320 ball", "documents_required": "Attestat, IELTS 5.5", "requirements": None},
    ],
    "Xəzər Universiteti": [
        # Son tarix dəyişir 25 İyul -> 1 Avqust (UPDATED gözlənilir)
        {"faculty": "Mühəndislik və tətbiqi elmlər", "program_name": "Süni intellekt", "degree": "Bachelor", "language": "English", "tuition_fee": "5600", "application_deadline": "1 Avqust 2026", "gpa_requirement": "320 ball", "documents_required": "Attestat, IELTS 5.5", "requirements": None},
    ],
}
