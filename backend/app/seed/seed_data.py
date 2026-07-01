"""Təkrarlana bilən demo/test üçün saxlanmış fixture datası.

Canlı skrap OpenRouter API açarından və saytların strukturundan asılıdır; bu fixture-lar
isə həmişə işləyən demo, dolu dashboard və dəyişiklik aşkarlama nümayişi təmin edir.

- SEED_UNIVERSITIES: ilkin "v1" vəziyyət (6 universitet, 30 proqram).
- UPDATES: sonrakı bir "skrap"ı təqlid edən dəyişikliklər (qiymət dəyişir, yeni
  ixtisas əlavə olunur) — change detection + insan yoxlaması axınını offline göstərmək üçün.

QEYD: `website_url` birbaşa kurs/proqram siyahısı səhifəsinə yönəlib. Bu saytlar statik
server-render olunur və canlı skrap (▶ pipeline) üçün etibarlı işləyir (Azərbaycan
universitet saytları JS-ağır/anti-bot olduğu üçün əvəzləndi).
"""

SEED_UNIVERSITIES = [
    {
        "name": "University of Kent",
        "website_url": "https://www.kent.ac.uk/courses/undergraduate",
        "programs": [
            {"faculty": "School of Computing", "program_name": "Computer Science", "degree": "Bachelor", "language": "English", "tuition_fee": "21900", "application_deadline": "31 January 2026", "gpa_requirement": "ABB", "documents_required": "Transcript, Personal Statement, IELTS 6.0", "requirements": None},
            {"faculty": "Kent Law School", "program_name": "Law", "degree": "Bachelor", "language": "English", "tuition_fee": "20800", "application_deadline": "31 January 2026", "gpa_requirement": "ABB", "documents_required": "Transcript, Reference, IELTS 6.5", "requirements": None},
            {"faculty": "School of Economics", "program_name": "Economics", "degree": "Bachelor", "language": "English", "tuition_fee": "20800", "application_deadline": "31 January 2026", "gpa_requirement": "ABB", "documents_required": "Transcript, IELTS 6.0", "requirements": None},
            {"faculty": "School of Psychology", "program_name": "Psychology", "degree": "Bachelor", "language": "English", "tuition_fee": "21900", "application_deadline": "31 January 2026", "gpa_requirement": "BBB", "documents_required": "Transcript, IELTS 6.5", "requirements": None},
            {"faculty": "School of Engineering", "program_name": "Mechanical Engineering", "degree": "Bachelor", "language": "English", "tuition_fee": "24000", "application_deadline": "31 January 2026", "gpa_requirement": "BBB", "documents_required": "Transcript, IELTS 6.0", "requirements": None},
        ],
    },
    {
        "name": "University of Manchester",
        "website_url": "https://www.manchester.ac.uk/study/undergraduate/courses/",
        "programs": [
            {"faculty": "Computer Science", "program_name": "Computer Science", "degree": "Bachelor", "language": "English", "tuition_fee": "32000", "application_deadline": "29 January 2026", "gpa_requirement": "AAA", "documents_required": "Transcript, Personal Statement, IELTS 6.5", "requirements": None},
            {"faculty": "Mechanical Engineering", "program_name": "Mechanical Engineering", "degree": "Bachelor", "language": "English", "tuition_fee": "33000", "application_deadline": "29 January 2026", "gpa_requirement": "AAA", "documents_required": "Transcript, IELTS 6.5", "requirements": None},
            {"faculty": "School of Social Sciences", "program_name": "Economics", "degree": "Bachelor", "language": "English", "tuition_fee": "28000", "application_deadline": "29 January 2026", "gpa_requirement": "AAA", "documents_required": "Transcript, IELTS 7.0", "requirements": None},
            {"faculty": "School of Law", "program_name": "Law", "degree": "Bachelor", "language": "English", "tuition_fee": "28000", "application_deadline": "29 January 2026", "gpa_requirement": "AAA", "documents_required": "Transcript, Reference, IELTS 7.0", "requirements": None},
            {"faculty": "Department of Chemistry", "program_name": "Chemistry", "degree": "Bachelor", "language": "English", "tuition_fee": "32000", "application_deadline": "29 January 2026", "gpa_requirement": "AAA", "documents_required": "Transcript, IELTS 6.5", "requirements": None},
        ],
    },
    {
        "name": "University of Sheffield",
        "website_url": "https://www.sheffield.ac.uk/undergraduate/courses",
        "programs": [
            {"faculty": "Computer Science", "program_name": "Computer Science", "degree": "Bachelor", "language": "English", "tuition_fee": "27950", "application_deadline": "31 January 2026", "gpa_requirement": "AAB", "documents_required": "Transcript, IELTS 6.5", "requirements": None},
            {"faculty": "Civil and Structural Engineering", "program_name": "Civil Engineering", "degree": "Bachelor", "language": "English", "tuition_fee": "28150", "application_deadline": "31 January 2026", "gpa_requirement": "AAA", "documents_required": "Transcript, IELTS 6.0", "requirements": None},
            {"faculty": "Department of Economics", "program_name": "Economics", "degree": "Bachelor", "language": "English", "tuition_fee": "24450", "application_deadline": "31 January 2026", "gpa_requirement": "AAB", "documents_required": "Transcript, IELTS 6.5", "requirements": None},
            {"faculty": "Department of Psychology", "program_name": "Psychology", "degree": "Bachelor", "language": "English", "tuition_fee": "27950", "application_deadline": "31 January 2026", "gpa_requirement": "AAA", "documents_required": "Transcript, IELTS 7.0", "requirements": None},
            {"faculty": "School of Architecture", "program_name": "Architecture", "degree": "Bachelor", "language": "English", "tuition_fee": "27950", "application_deadline": "31 January 2026", "gpa_requirement": "AAB", "documents_required": "Portfolio, Transcript, IELTS 6.5", "requirements": None},
        ],
    },
    {
        "name": "University of Leeds",
        "website_url": "https://courses.leeds.ac.uk/course-search/undergraduate-courses",
        "programs": [
            {"faculty": "School of Computing", "program_name": "Computer Science", "degree": "Bachelor", "language": "English", "tuition_fee": "29000", "application_deadline": "31 January 2026", "gpa_requirement": "AAA", "documents_required": "Transcript, IELTS 6.0", "requirements": None},
            {"faculty": "School of Mechanical Engineering", "program_name": "Mechanical Engineering", "degree": "Bachelor", "language": "English", "tuition_fee": "29500", "application_deadline": "31 January 2026", "gpa_requirement": "AAA", "documents_required": "Transcript, IELTS 6.0", "requirements": None},
            {"faculty": "School of Law", "program_name": "Law", "degree": "Bachelor", "language": "English", "tuition_fee": "24500", "application_deadline": "31 January 2026", "gpa_requirement": "AAA", "documents_required": "Transcript, Reference, IELTS 6.5", "requirements": None},
            {"faculty": "Economics", "program_name": "Economics", "degree": "Bachelor", "language": "English", "tuition_fee": "26000", "application_deadline": "31 January 2026", "gpa_requirement": "AAA", "documents_required": "Transcript, IELTS 6.5", "requirements": None},
            {"faculty": "School of Medicine", "program_name": "Medicine", "degree": "Bachelor", "language": "English", "tuition_fee": "44500", "application_deadline": "15 October 2025", "gpa_requirement": "AAA", "documents_required": "UCAT, Transcript, IELTS 7.0", "requirements": None},
        ],
    },
    {
        "name": "University of Surrey",
        "website_url": "https://www.surrey.ac.uk/undergraduate/courses",
        "programs": [
            {"faculty": "Computer Science and Electronic Engineering", "program_name": "Computer Science", "degree": "Bachelor", "language": "English", "tuition_fee": "23800", "application_deadline": "31 January 2026", "gpa_requirement": "AAB", "documents_required": "Transcript, IELTS 6.5", "requirements": None},
            {"faculty": "Computer Science and Electronic Engineering", "program_name": "Electrical and Electronic Engineering", "degree": "Bachelor", "language": "English", "tuition_fee": "23800", "application_deadline": "31 January 2026", "gpa_requirement": "AAB", "documents_required": "Transcript, IELTS 6.0", "requirements": None},
            {"faculty": "Surrey Business School", "program_name": "Business Management", "degree": "Bachelor", "language": "English", "tuition_fee": "22600", "application_deadline": "31 January 2026", "gpa_requirement": "ABB", "documents_required": "Transcript, IELTS 6.5", "requirements": None},
            {"faculty": "School of Psychology", "program_name": "Psychology", "degree": "Bachelor", "language": "English", "tuition_fee": "23800", "application_deadline": "31 January 2026", "gpa_requirement": "AAB", "documents_required": "Transcript, IELTS 6.5", "requirements": None},
            {"faculty": "Civil and Environmental Engineering", "program_name": "Civil Engineering", "degree": "Bachelor", "language": "English", "tuition_fee": "23800", "application_deadline": "31 January 2026", "gpa_requirement": "ABB", "documents_required": "Transcript, IELTS 6.0", "requirements": None},
        ],
    },
    {
        "name": "University of Nottingham",
        "website_url": "https://www.nottingham.ac.uk/ugstudy/courses",
        "programs": [
            {"faculty": "School of Computer Science", "program_name": "Computer Science", "degree": "Bachelor", "language": "English", "tuition_fee": "30000", "application_deadline": "31 January 2026", "gpa_requirement": "AAA", "documents_required": "Transcript, IELTS 6.0", "requirements": None},
            {"faculty": "Faculty of Engineering", "program_name": "Mechanical Engineering", "degree": "Bachelor", "language": "English", "tuition_fee": "30750", "application_deadline": "31 January 2026", "gpa_requirement": "AAA", "documents_required": "Transcript, IELTS 6.0", "requirements": None},
            {"faculty": "School of Economics", "program_name": "Economics", "degree": "Bachelor", "language": "English", "tuition_fee": "23000", "application_deadline": "31 January 2026", "gpa_requirement": "AAA", "documents_required": "Transcript, IELTS 6.5", "requirements": None},
            {"faculty": "School of Law", "program_name": "Law", "degree": "Bachelor", "language": "English", "tuition_fee": "23000", "application_deadline": "31 January 2026", "gpa_requirement": "AAA", "documents_required": "Transcript, Reference, IELTS 7.0", "requirements": None},
            {"faculty": "School of Pharmacy", "program_name": "Pharmacy", "degree": "Master", "language": "English", "tuition_fee": "30000", "application_deadline": "31 January 2026", "gpa_requirement": "AAB", "documents_required": "Transcript, IELTS 7.0", "requirements": None},
        ],
    },
]


# Sonrakı bir "skrap"ı təqlid edən dəyişikliklər (universitet adına görə açar).
# Change detection nümayişi: mövcud ixtisasın qiyməti/son tarixi dəyişir + 1 yeni ixtisas.
UPDATES = {
    "University of Kent": [
        # Mövcud ixtisas — təhsil haqqı 21900 -> 22600 (UPDATED gözlənilir)
        {"faculty": "School of Computing", "program_name": "Computer Science", "degree": "Bachelor", "language": "English", "tuition_fee": "22600", "application_deadline": "31 January 2026", "gpa_requirement": "ABB", "documents_required": "Transcript, Personal Statement, IELTS 6.0", "requirements": None},
        # Tamamilə yeni ixtisas (NEW gözlənilir)
        {"faculty": "School of Computing", "program_name": "Artificial Intelligence", "degree": "Bachelor", "language": "English", "tuition_fee": "23400", "application_deadline": "31 January 2026", "gpa_requirement": "AAB", "documents_required": "Transcript, IELTS 6.5", "requirements": None},
    ],
    "University of Manchester": [
        # Son tarix dəyişir 29 January -> 15 January (UPDATED gözlənilir)
        {"faculty": "Computer Science", "program_name": "Computer Science", "degree": "Bachelor", "language": "English", "tuition_fee": "32000", "application_deadline": "15 January 2026", "gpa_requirement": "AAA", "documents_required": "Transcript, Personal Statement, IELTS 6.5", "requirements": None},
    ],
}
