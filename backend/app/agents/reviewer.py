import os
import re
import requests
import json

# Modelin "düşüncə/meta" mətnini (yekun cavab yerinə) aşkarlayan işarələr
_META_MARKERS = [
    "we need to", "let's craft", "let's count", "that's 4 sentence", "that's 3 sentence",
    "executive summary in azerbaijani", "must mention", "must be concise", "keep 3-4",
    "provide summary", "the metrics", "so we can say", "here is", "here's the",
    "okay,", "i will", "i'll", "as an ai",
]


class ReviewerAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("OPENROUTER_MODEL_NAME", "openrouter/free")
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def _fallback_summary(self, university_name, change_report, avg_confidence, pending_count) -> str:
        """Metriklərdən deterministik, təmiz idarəçi icmalı qurur (model zibil verəndə)."""
        new = len(change_report.get("new", []))
        updated = len(change_report.get("updated", []))
        stable = change_report.get("unchanged_count", 0)
        avg = f"{avg_confidence:.2f}" if avg_confidence is not None else "—"
        return (
            f"[TƏSDİQLƏNDİ] {university_name} üzrə analiz uğurla tamamlandı: {new} yeni ixtisas "
            f"və {updated} yenilənmiş sahə bazaya inteqrasiya edildi, {stable} ixtisas stabil qaldı. "
            f"Orta etibarlılıq balı {avg}; aşağı etibarlılıqlı {pending_count} qeyd insan yoxlamasına yönləndirildi."
        )

    def _clean_summary(self, text: str) -> str:
        """Model cavabından yalnız yekun icmalı çıxarır: <think> bloklarını, markdown-ı və
        meta/planlama mətnini atır. Zibil görünürsə boş qaytarır (fallback işə düşür)."""
        if not text:
            return ""
        # Reasoning modellərinin <think>...</think> bloklarını sil
        text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"```[a-z]*|```", "", text).strip()

        # Təsdiq tagı varsa, oradan başlayan hissəni götür (əvvəldəki planlama atılır)
        m = re.search(r"\[\s*T[ƏEÆ]SD[İIi]QL[ƏEÆ]ND[İIi]\s*\]", text, flags=re.IGNORECASE)
        has_tag = m is not None
        if m:
            text = text[m.start():].strip()

        low = text.lower()
        # Hələ də ingilis meta/planlama mətni varsa — zibil, fallback-a düş
        if any(mk in low for mk in _META_MARKERS):
            return ""
        # Təsdiq tagı yoxdursa və ya həddindən uzundursa — etibarsız
        if not has_tag or len(text) > 900:
            return ""
        return text

    def review_pipeline(self, university_name: str, target_url: str, total_valid: int,
                        change_report: dict, avg_confidence: float = None, pending_count: int = 0) -> str:
        """Bütün agentlərin işini icmal edir və yekun idarəçi hesabatı hazırlayır"""
        if not self.api_key:
            return self._fallback_summary(university_name, change_report, avg_confidence, pending_count)

        # Agentlərin çıxardığı nəticələrin xülasəsi
        summary_metrics = {
            "university": university_name,
            "analyzed_url": target_url,
            "total_extracted_and_valid_count": total_valid,
            "new_majors_detected": len(change_report.get("new", [])),
            "updated_fields_detected": len(change_report.get("updated", [])),
            "stable_unchanged_majors": change_report.get("unchanged_count", 0),
            "average_confidence": avg_confidence,
            "sent_to_human_review": pending_count,
        }

        # Modelə tapşırıq veririk
        prompt = f"""
        You are the 'Reviewer Agent' (The Supervisor) of the UniAgent Multi-Agent system. 
        Review the following execution metrics of the university data extraction pipeline and write a professional, high-level executive summary of the operation in Azerbaijani language.
        
        Operation Metrics:
        {json.dumps(summary_metrics, indent=2)}
        
        Guidelines:
        1. Keep the summary concise (maximum 3-4 sentences).
        2. Use a professional, technical, and analytical tone.
        3. Start with an approval tag exactly: "[TƏSDİQLƏNDİ]".
        4. Explicitly mention if any data changes (new programs or updated fields) were successfully integrated into the database.
        5. CRITICAL: Output ONLY the final Azerbaijani summary text. Do NOT include your reasoning, planning notes, English commentary, quotes, or restate the task. Return just the summary, nothing else.
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.2
        }

        try:
            response = requests.post(self.url, json=payload, headers=headers, timeout=20)
            if response.status_code == 200:
                raw = response.json()['choices'][0]['message']['content'].strip()
                cleaned = self._clean_summary(raw)
                if cleaned:
                    print("[Reviewer Agent]: Yekun əməliyyat hesabatı imzalandı.")
                    return cleaned
                print("[Reviewer Agent]: model meta/zibil qaytardı — deterministik icmala keçilir.")
        except Exception as e:
            print(f"[Reviewer Agent Xətası]: {str(e)}")

        # Model ilişərsə və ya təmiz icmal vermirsə — həmişə etibarlı deterministik fallback
        return self._fallback_summary(university_name, change_report, avg_confidence, pending_count)