import os
import requests
import json
import re

class ExtractionAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = "openai/gpt-oss-120b:free"
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def clean_html(self, raw_html: str) -> str:
        """HTML-dən skriptləri, stilləri və lazımsız teqləri təmizləyir"""
        # Script və Style teqlərinin içini tamamilə silirik
        text = re.sub(r'<script[^>]*>([\s\S]*?)</script>', '', raw_html)
        text = re.sub(r'<style[^>]*>([\s\S]*?)</style>', '', text)
        # Bütün HTML teqlərini təmizləyirik
        text = re.sub(r'<[^>]+>', ' ', text)
        # Çoxlu boşluq və sətir keçidlərini tək boşluğa endiririk
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def extract_programs(self, raw_html: str) -> list:
        """Təmizlənmiş mətndən universitet ixtisaslarını JSON formatında çıxarır"""
        if not self.api_key:
            print("[Extraction Agent Xətası]: API açarı tapılmadı!")
            return []

        # HTML təmizləmə filtrini işə salırıq
        cleaned_text = self.clean_html(raw_html)
        
        # Modelin kontekstini qorumaq üçün mətni optimallaşdırırıq
        prompt_text = cleaned_text[:15000]

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
        - requirements (Any specific requirement note or null)

        Rules:
        1. Return a strict JSON array of objects. Example format:
           [
             {{"faculty": "Bakalavriat", "program_name": "Maliyyə", "degree": "Bachelor", "language": "Azerbaijani", "tuition_fee": "2600", "requirements": null}}
           ]
        2. Do not include markdown wraps like ```json ... ``` or any explanatory text. Return the raw JSON string array only.
        3. If no programs are found, return an empty array [].
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
                
                # Əgər model inadkarlıq edib markdown daxilində qaytararsa təmizləyirik
                if ai_res.startswith("```"):
                    ai_res = re.sub(r'```json|```', '', ai_res).strip()
                
                programs = json.loads(ai_res)
                print(f"[Extraction Agent]: {len(programs)} dənə ixtisas mətndən qoparılıb gətirildi.")
                return programs
        except Exception as e:
            print(f"[Extraction Agent Xətası]: {str(e)}")
            
        return []