import os
import json
import time
from google import genai
from google.genai import types

class AIExtractor:
    def __init__(self, api_key, prompts_dir):
        self.client = genai.Client(api_key=api_key)
        self.prompts_dir = prompts_dir
        self.model_id = 'gemini-3.5-flash-lite'

    def get_template(self):
        """Skema JSON statis yang diekspektasikan oleh sistem lama."""
        return {
            "ffsDate": "", "launchDate": "", "aum": 0.0, "totalAum": 0, "currency": "IDR",
            "topHoldings": [], "portfolioAllocations": [],
            "investmentObjective": "", "mfType": "", "productCode": "", 
            "productName": "", "ffsPeriod": ""
        }

    def _load_prompt(self, mi_name):
        """Load instruksi spesifik MI dari file txt."""
        filepath = os.path.join(self.prompts_dir, f"{mi_name.lower()}.txt")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Prompt file untuk MI '{mi_name}' tidak ditemukan di {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    def extract(self, pdf_text, mi_name, max_retries=3):
        """Fungsi utama untuk mengekstrak PDF menjadi JSON dengan Auto-Retry."""
        system_prompt = self._load_prompt(mi_name)
        schema_str = json.dumps(self.get_template(), indent=2)
        
        full_prompt = f"""
        {system_prompt}
        
        INSTRUKSI OUTPUT:
        Keluarkan data HANYA dalam format JSON baku...
        {schema_str}
        
        TEKS PDF FUND FACT SHEET:
        {pdf_text}
        """
        
        # Loop buat nyoba maksimal 3 kali kalau kena error 503
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.0 
                    )
                )
                return self._validate_and_parse(response.text)
            
            except Exception as e:
                error_msg = str(e)
                if "503" in error_msg:
                    print(f"[WARNING] Server sibuk atau Limit RPM tercapai. Coba lagi dalam 60 detik... (Percobaan {attempt + 1}/{max_retries})")
                    time.sleep(60)
                else:
                    print(f"[ERROR] Eksekusi Gemini gagal untuk MI {mi_name}: {e}")
                    break
            return self.get_template()

    def _validate_and_parse(self, response_text):
        """Memastikan output adalah JSON valid dan struktur keys terjamin."""
        template = self.get_template()
        try:
            data = json.loads(response_text)
            for key, default_value in template.items():
                if key not in data or data[key] is None:
                    data[key] = default_value
            return data
        except json.JSONDecodeError:
            print(f"[ERROR] Gemini mengembalikan JSON tidak valid:\n{response_text}")
            return template