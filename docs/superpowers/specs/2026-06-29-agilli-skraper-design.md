# Ağıllı Skraper — Dizayn Spesifikasiyası

Tarix: 2026-06-29
Layihə: uni-agent-system

## Problem

Mövcud skraper (`helper_scrape`, urllib) real yad universitet saytlarında uğursuz olur:
- JS-render saytlar boş shell qaytarır (TUM, Helsinki).
- Bot bloku (Tartu 403).
- `research.py` link seçiminə LLM sorğusu xərcləyir (gündə 50 limit).
- `extraction.py` mətni ilk 15000 simvolla kəsir → dərin proqram siyahıları itir.

## Məqsəd

İxtisasları real saytlardan etibarlı tapan skraper. LLM sorğusunu minimuma endirmək (gündəlik 50 limit kritikdir).

## Qərarlar (brainstorm)

- **Fetch:** Playwright (real brauzer), alınmasa urllib fallback.
- **Crawl:** 2 səviyyə + `sitemap.xml`.
- **LLM:** yalnız son extraction mərhələsində. Link seçimi tam heuristik.

## Arxitektura

### 1. Yeni modul: `backend/app/agents/crawler.py`

```
fetch(url) -> str
```
- Əvvəl Playwright (headless chromium) ilə açır, `networkidle` gözləyir, render olunmuş HTML qaytarır.
- Playwright yoxdursa/çökərsə → urllib fallback (mövcud `helper_scrape` məntiqi, User-Agent başlığı ilə).
- Xəta olarsa boş string qaytarır (pipeline-i dağıtmır).

```
discover_sitemap_urls(base_url) -> list[str]
```
- `base_url/sitemap.xml` oxuyur (varsa), `<loc>` URL-lərini çıxarır.
- Sitemap yoxdursa boş siyahı.

```
rank_candidate_urls(hrefs, sitemap_urls, base_url) -> list[str]
```
- Bütün daxili linkləri birləşdirir (yalnız `base_url` domeni).
- Hər URL-ə açar söz xalı verir:
  `bachelor, undergraduate, programs, program, ixtisas, bakalavr, faculties, faculty, admission, study, degree, qebul`.
- Sosial/fayl linklərini (`facebook`, `.pdf`, `.jpg` ...) atır.
- Xalına görə sıralayıb **top 5** qaytarır. LLM YOXDUR.

### 2. `extraction.py` dəyişikliyi

- 15000 simvol kəsimi götürülür.
- Yeni `_chunk_text(text, size=12000, overlap=500) -> list[str]`.
- `extract_programs` hər chunk üçün LLM çağırır, nəticələri birləşdirir.
- `_dedupe(programs)` — `program_name` (normallaşdırılmış) üzrə dublikatları silir.
- API açarı yoxsa boş siyahı (mövcud davranış).

### 3. Pipeline (`main.py`) dəyişikliyi

`run_university_agent_pipeline` axını:

1. `home_html = crawler.fetch(base_url)`  *(əvvəl helper_scrape)*
2. `sitemap = crawler.discover_sitemap_urls(base_url)`
3. `hrefs = research_agent.extract_all_links(home_html, base_url)`
4. `candidates = crawler.rank_candidate_urls(hrefs, sitemap, base_url)`  *(əvvəl LLM discover)*
5. Hər candidate üçün `crawler.fetch`, mətnləri topla (ən çox 5 səhifə).
6. Birləşmiş mətn → `extraction_agent.extract_programs` (chunking).
7. Qalan stage-lər **dəyişməz**: validation → change detector → integrate → reviewer.

`helper_scrape` saxlanılır (fallback kimi crawler içində istifadə olunur).
Audit üçün hər çəkilən səhifə `ScrapedPage`-ə yazılır (mövcud davranış).

## Komponent sərhədləri

| Modul | Vəzifə | Asılılıq |
|-------|--------|----------|
| `crawler.py` | HTML çəkmək, link sıralamaq, sitemap | playwright (opsional), urllib, bs4 |
| `research.py` | `extract_all_links` saxlanır; LLM `discover_specialty_url` artıq pipeline-da çağırılmır | — |
| `extraction.py` | mətndən ixtisas çıxarmaq (chunk + dedupe) | OpenRouter |
| `main.py` | orkestrasiya | yuxarıdakılar |

## Xəta idarəsi

- Playwright import/runtime xətası → urllib fallback, log.
- Səhifə boş → o səhifəni keç, digər candidate-lərə davam.
- Bütün candidate boş → mövcud "İxtisas tapılmadı" cavabı.
- LLM 429 (limit) → boş siyahı (mövcud davranış, memory-də qeyd).

## Test

- `crawler.rank_candidate_urls` — unit test: keyword xal sıralaması.
- `crawler.discover_sitemap_urls` — sabit XML fixture-dən parse.
- `extraction._chunk_text` / `_dedupe` — unit test.
- `fetch` üçün şəbəkə testi yox (mock/skip).

## Əhatə xaricində (YAGNI)

- Paralel crawl, cache, robots.txt hörməti.
- 2-dən artıq crawl səviyyəsi.
- Yeni dependency-lər istisna olmaqla (playwright) infrastruktur dəyişikliyi.
