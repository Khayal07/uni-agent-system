import os
import requests
import json
import re


def parse_json_block(text: str):
    """Modelin cavabından JSON çıxarır: <think> tagları, markdown fence və artıq mətnə dözümlü.

    Uğursuz olarsa None qaytarır."""
    if not text:
        return None
    # Reasoning modellərinin <think>...</think> bloklarını silirik
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
    # Markdown fence təmizliyi
    text = re.sub(r"```json|```", "", text).strip()
    # Birbaşa parse cəhdi
    try:
        return json.loads(text)
    except Exception:
        pass
    # İlk JSON massiv və ya obyektini tapıb parse edirik
    match = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", text)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            return None
    return None


class ExtractionAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("OPENROUTER_MODEL_NAME", "openrouter/free")
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def clean_html(self, raw_html: str) -> str:
        """HTML-dən skriptləri, stilləri və lazımsız teqləri təmizləyib təmiz mətn qaytarır.

        Əsas üsul BeautifulSoup-dur; hər hansı səbəbdən alınmasa regex-ə geri düşür."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(raw_html, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text(separator=" ")
            return re.sub(r"\s+", " ", text).strip()
        except Exception:
            # Regex fallback
            text = re.sub(r'<script[^>]*>([\s\S]*?)</script>', '', raw_html)
            text = re.sub(r'<style[^>]*>([\s\S]*?)</style>', '', text)
            text = re.sub(r'<[^>]+>', ' ', text)
            return re.sub(r'\s+', ' ', text).strip()

    def _chunk_text(self, text: str, size: int = 12000, overlap: int = 500) -> list:
        """Uzun mətni üst-üstə düşən hissələrə bölür (15000 kəsimini əvəz edir)."""
        if len(text) <= size:
            return [text]
        chunks, start = [], 0
        while start < len(text):
            chunks.append(text[start:start + size])
            start += size - overlap
        return chunks

    def _dedupe(self, programs: list) -> list:
        """program_name (normallaşdırılmış) üzrə dublikatları silir."""
        seen, out = set(), []
        for p in programs:
            key = (p.get("program_name") or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(p)
        return out

    def extract_programs(self, raw_html: str) -> list:
        """Təmizlənmiş mətndən universitet ixtisaslarını çıxarır (chunk + dedupe)"""
        if not self.api_key:
            print("[Extraction Agent Xətası]: API açarı tapılmadı!")
            return []

        cleaned_text = self.clean_html(raw_html)
        all_programs = []
        for chunk in self._chunk_text(cleaned_text):
            all_programs.extend(self._extract_chunk(chunk))
        result = self._dedupe(all_programs)
        print(f"[Extraction Agent]: dedupe sonrası {len(result)} ixtisas.")
        return result

    def _extract_chunk(self, prompt_text: str) -> list:
        """Bir mətn hissəsindən LLM ilə ixtisasları çıxarır."""

        prompt = f"""
        You are the 'Extraction Agent'. Analyze the following text extracted from a university website and extract all available academic programs/majors.

        Text:
        {prompt_text}

        Extract the following fields for each program:
        - faculty (e.g., "Rəqəmsal İqtisadiyyat", "Bakalavriat", or faculty name if specified)
        - program_name (e.g., "Kompüter mühəndisliyi", "Maliyyə")
        - degree (Must be exactly "Bachelor" or "Master")
        - language (e.g., "Azerbaijani", "English", "Russian", or combined like "Azerbaijani, Eng")
        - tuition_fee (Extract only the numbers as a string, e.g., "2200", "2500". If free, write "0")
        - application_deadline (Application/admission deadline date if present, e.g., "31 Avqust 2026", or null)
        - gpa_requirement (Minimum GPA / score requirement if present, e.g., "3.0", "250 ball", or null)
        - documents_required (Required documents/admission requirements if listed, short text, or null)
        - requirements (Any other specific requirement note or null)

        Rules:
        1. Return a strict JSON array of objects. Example format:
           [
             {{"faculty": "Bakalavriat", "program_name": "Maliyyə", "degree": "Bachelor", "language": "Azerbaijani", "tuition_fee": "2600", "application_deadline": "31 Avqust 2026", "gpa_requirement": null, "documents_required": "Attestat, şəxsiyyət vəsiqəsi", "requirements": null}}
           ]
        2. Only extract values that actually appear in the text. If a field is unknown, use null. Do not invent data.
        3. Do not include markdown wraps like ```json ... ``` or any explanatory text. Return the raw JSON string array only.
        4. If no programs are found, return an empty array [].
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
            "temperature": 0.1
        }

        try:
            response = requests.post(self.url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                ai_res = response.json()['choices'][0]['message']['content'].strip()
                programs = parse_json_block(ai_res)
                if not isinstance(programs, list):
                    print(f"[Extraction Agent Xətası]: JSON massiv kimi parse oluna bilmədi.")
                    return []
                print(f"[Extraction Agent]: {len(programs)} dənə ixtisas mətndən qoparılıb gətirildi.")
                return programs
        except Exception as e:
            print(f"[Extraction Agent Xətası]: {str(e)}")
            
        return []