import os
import requests
import json
import re
from .extraction import parse_json_block

class ResearchAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("OPENROUTER_MODEL_NAME", "openrouter/free")
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def _raw_hrefs(self, raw_html: str) -> list:
        """HTML-dən href dəyərlərini yığır: əvvəlcə BeautifulSoup, alınmasa regex."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(raw_html, "html.parser")
            return [a.get("href") for a in soup.find_all("a", href=True)]
        except Exception:
            return re.findall(r'href=["\'](https?://.*?|/.*?)["\']', raw_html)

    def extract_all_links(self, raw_html: str, base_url: str) -> list:
        """HTML daxilindən bütün daxili (internal) linkləri yığır"""
        links = self._raw_hrefs(raw_html)
        cleaned_links = []

        for link in links:
            if not link:
                continue
            # Sosial şəbəkə və lazımsız fayl linklərini filterləyirik
            if any(x in link for x in ["facebook", "instagram", "linkedin", "twitter", ".pdf", ".jpg", ".png"]):
                continue
            
            # Nisbi (relative) linkləri tam linkə çeviririk
            if link.startswith("/"):
                # base_url-in sonundakı slash-i təmizləyib birləşdiririk
                full_link = f"{base_url.rstrip('/')}{link}"
            else:
                full_link = link
                
            if full_link not in cleaned_links and base_url in full_link:
                cleaned_links.append(full_link)
                
        return cleaned_links[:40]  # Modelin kontekstini doldurmamaq üçün ilk 40 link kifayətdir

    def discover_specialty_url(self, raw_html: str, base_url: str) -> str:
        """Agent ağıllı şəkildə ixtisaslar olan ən doğru linki seçir"""
        if not self.api_key:
            return base_url

        # 1. Səhifədəki linkləri çıxarırıq
        extracted_links = self.extract_all_links(raw_html, base_url)
        
        if not extracted_links:
            return base_url

        # 2. Agentə tapşırıq (Prompt) hazırlayırıe
        prompt = f"""
        You are the 'Research Agent' of a University Data System. Your job is to analyze a list of URLs extracted from a university website home page and identify WHICH URL is most likely to contain the official list of academic programs, bachelor majors, faculties, or admission specialties.

        Base URL: {base_url}
        Available URLs to choose from:
        {json.dumps(extracted_links, indent=2)}

        Rules:
        1. Select ONLY ONE URL from the list that directly relates to 'bachelor', 'undergraduate', 'programs', 'specialties', 'ixtisaslar', 'bakalavriat', or 'faculties'.
        2. Return a strict JSON response with exactly one key named "target_url".
        3. Do not include markdown blocks like ```json ... ``` or thinking tags. Return raw JSON text only.
        4. If no specific URL matches, return the Base URL.
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500
        }

        try:
            response = requests.post(self.url, json=payload, headers=headers, timeout=20)
            if response.status_code == 200:
                ai_res = response.json()['choices'][0]['message']['content'].strip()
                data = parse_json_block(ai_res)
                if isinstance(data, dict):
                    target = data.get("target_url", base_url)
                    print(f"[Research Agent]: Ixtisas səhifəsi tapıldı -> {target}")
                    return target
        except Exception as e:
            print(f"[Research Agent Xətası]: {str(e)}")
            
        return base_url