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


def _urllib_fetch(url: str, timeout: int = 20) -> str:
    """urllib fallback — User-Agent başlığı ilə xam HTML çəkir."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"},
        )
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[Crawler urllib xətası] {url}: {e}")
        return ""


def _playwright_fetch(url: str, timeout: int = 20) -> str:
    """Playwright ilə JS-render olunmuş HTML; alınmasa boş string."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120 Safari/537.36"))
            page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
            # JS-render üçün qısa əlavə gözləmə (networkidle bəzi saytlarda heç sakitləşmir)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            html = page.content()
            browser.close()
            return html or ""
    except Exception as e:
        print(f"[Crawler Playwright xətası] {url}: {e} — urllib-ə keçilir")
        return ""


def fetch(url: str, timeout: int = 20) -> str:
    """HTML çəkir: Playwright (JS-render) və urllib (statik server-render) — uzununu seçir.

    JS saytlarda urllib boş shell verir, Playwright qazanır; UCL kimi statik saytlarda
    isə Playwright erkən shell tutur, urllib tam siyahını verir. İkisindən uzunu götürülür."""
    pw = _playwright_fetch(url, timeout)
    ul = _urllib_fetch(url, timeout)
    return pw if len(pw) >= len(ul) else ul


def discover_sitemap_urls(base_url: str) -> list:
    """base_url/sitemap.xml oxuyub <loc> URL-lərini qaytarır (yoxdursa boş)."""
    sitemap_url = base_url.rstrip("/") + "/sitemap.xml"
    xml = _urllib_fetch(sitemap_url, timeout=10)
    return _parse_sitemap_xml(xml) if xml else []
