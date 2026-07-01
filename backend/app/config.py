"""Mərkəzləşmiş konfiqurasiya — bütün env oxumaları bir yerdən keçir.

Docker-compose env-ləri `env_file`/`environment` ilə ötürür; lokalda isə
`load_dotenv()` `.env` faylını yükləyir ki, tətbiq konteynersiz də işləsin.
"""
import os
import sys
from dotenv import load_dotenv

# Windows konsolunda (cp1252) Azərbaycan hərfli print-lərin çökməməsi üçün UTF-8-ə keçirik
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Lokal işə salmada .env-i yükləyirik (Docker-də onsuz da env-lər mövcuddur)
load_dotenv()

# Verilənlər bazası — təyin olunmayıbsa lokal SQLite fallback (Postgres-siz iş üçün)
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./app.db"

# OpenRouter (AI agentləri üçün)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Etibarlılıq balı bu həddən aşağı olanlar insan yoxlamasına göndərilir
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))

# Semantic dəyişiklik aşkarlama: mətn sahələrində oxşarlıq bu həddən yüksəkdirsə,
# fərq "formatlaşma" sayılır və DƏYİŞİKLİK kimi qeyd olunmur (yanlış xəbərdarlıq azalır).
SEMANTIC_SIMILARITY_THRESHOLD = float(os.getenv("SEMANTIC_SIMILARITY_THRESHOLD", "0.90"))

# Orta etibarlılıq bu həddən aşağı olduqda extraction strict rejimdə bir dəfə təkrarlanır.
# Token qənaəti üçün "false" ilə söndürülə bilər (OpenRouter free limit — 50/gün).
EXTRACTION_RETRY_ENABLED = os.getenv("EXTRACTION_RETRY_ENABLED", "true").lower() == "true"
