# UniAgent — University Data Intelligence Agent

Universitet saytlarını araşdıran, proqram (ixtisas) məlumatlarını çıxaran, əvvəlki
məlumatla müqayisə edən və şübhəli nəticələri insan yoxlamasına göndərən **5 agentli**
sistem.

## Agentlər (pipeline)

```
Universitet URL → Research → Extraction → Validation → Change Detection → Review
                                                              ↓
                                          Etibarlılıq balı → Avtomatik qəbul / İnsan yoxlaması
```

| Agent | Fayl | Vəzifə |
|-------|------|--------|
| Research | `agents/research.py` | Ana səhifədən ixtisaslar olan ən doğru linki seçir (LLM) |
| Extraction | `agents/extraction.py` | HTML-i təmizləyir (BeautifulSoup) və 8 sahəni çıxarır (LLM) |
| Validation | `agents/validation.py` | Hər sahəni səhifə mətni ilə müqayisə edir, **qayda-əsaslı confidence** hesablayır |
| Change Detection | `agents/change_detector.py` | (ad, dərəcə) açarı ilə müqayisə, dəyişən sahələri `ChangeLog`-a yazır |
| Review | `agents/reviewer.py` | Yekun icmal; aşağı confidence-li məlumatı insan yoxlamasına göndərir |

Çıxarılan sahələr: proqram adı, fakültə, dərəcə, dil, təhsil haqqı, **müraciət tarixi,
GPA tələbi, tələb olunan sənədlər**.

## Quraşdırma

`.env` faylı (nümunə):

```env
DATABASE_URL=postgresql://uniuser:unipass@db:5432/unidb
POSTGRES_USER=uniuser
POSTGRES_PASSWORD=unipass
POSTGRES_DB=unidb
OPENROUTER_API_KEY=sk-or-...        # AI agentləri üçün (OpenRouter)
CONFIDENCE_THRESHOLD=0.75           # bundan aşağı → insan yoxlaması
```

Docker ilə işə salma:

```bash
docker-compose up --build
# UI: http://localhost:8000
```

## İstifadə

1. **Demo Datasını Yüklə** düyməsi (`POST /seed`) — 6 universitet, 30+ ixtisas (LLM tələb etmir).
2. Universitet sətrində **Başlat** — canlı pipeline (Research→...→Review, OpenRouter açarı lazımdır).
3. **↻ (simulyasiya)** düyməsi (`POST /universities/{id}/simulate-update`) — növbəti skrapı
   təqlid edir; dəyişiklik aşkarlamanı və köhnə→yeni panelini API açarı olmadan göstərir.
4. Aşağı etibarlılıqlı məlumatlar **İnsan Təsdiqi Paneli**ndə görünür → **Təsdiqlə / Rədd et**.

## Əsas endpointlər

| Metod | Yol | Təsvir |
|-------|-----|--------|
| POST | `/seed` | Fixture datasını yükləyir |
| POST | `/universities/{id}/run-agent-pipeline` | Tam 5-agentli canlı pipeline |
| POST | `/universities/{id}/simulate-update` | Dəyişiklik aşkarlama simulyasiyası (offline) |
| GET | `/universities/{id}/programs` | Universitetin bütün proqramları |
| GET | `/universities/{id}/changes` | Köhnə→yeni dəyişiklik tarixçəsi |
| GET | `/programs/pending` | İnsan yoxlaması gözləyənlər |
| POST | `/programs/{id}/approve` · `/reject` | İnsan qərarı |

## Testlər

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -q
```

Testlər LLM çağırmır — Validation (source-match, format, confidence), Change Detector
(yanlış "yeni" xəbərdarlığının olmaması daxil), HTML təmizliyi, JSON parse və sahə üzrə
Precision/Recall nümunəsi yoxlanılır.
