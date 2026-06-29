import re
import ssl
import urllib.request

# İxtisas səhifələrini tanıyan açar sözlər (xal verilir, LLM YOXDUR)
PROGRAM_KEYWORDS = [
    "bachelor", "undergraduate", "program", "programs", "ixtisas", "ixtisaslar",
    "bakalavr", "bakalavriat", "faculty", "faculties", "admission", "study",
    "degree", "qebul", "qəbul",
]
# Atılan linklər
_SKIP = ["facebook", "instagram", "linkedin", "twitter", "youtube",
         ".pdf", ".jpg", ".jpeg", ".png", ".gif", "mailto:", "tel:"]


def _parse_sitemap_xml(xml: str) -> list:
    """sitemap.xml mətnindən <loc> URL-lərini çıxarır."""
    return re.findall(r"<loc>\s*(.*?)\s*</loc>", xml, flags=re.IGNORECASE)


def _score(url: str) -> int:
    low = url.lower()
    return sum(1 for kw in PROGRAM_KEYWORDS if kw in low)


def rank_candidate_urls(hrefs: list, sitemap_urls: list, base_url: str) -> list:
    """Daxili linkləri açar söz xalına görə sıralayıb top 5 qaytarır (LLM yox)."""
    domain = base_url.rstrip("/")
    pool, seen = [], set()
    for url in list(hrefs) + list(sitemap_urls):
        if not url:
            continue
        low = url.lower()
        if any(s in low for s in _SKIP):
            continue
        if not url.startswith(domain):
            continue
        if url in seen:
            continue
        seen.add(url)
        pool.append(url)
    # Yalnız ən azı bir açar sözü olanlar, xalına görə azalan
    scored = [(u, _score(u)) for u in pool]
    scored = [t for t in scored if t[1] > 0]
    scored.sort(key=lambda t: t[1], reverse=True)
    return [u for u, _ in scored[:5]]
