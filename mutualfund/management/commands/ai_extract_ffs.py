import os
import time
from django.core.management.base import BaseCommand
from mutualfund.services.pdf_service import PDFService
from mutualfund.services.sql_service import SQLService
from mutualfund.services.rename_service import RenameService
from mutualfund.services.ksei_service import KseiService
from mutualfund.services.pefindo_service import PefindoService
from mutualfund.utils import normalize_pdf_text
from mutualfund.ai.extractor import AIExtractor

class Command(BaseCommand):
    help = 'Modular: Extract FFS data using AI, generate SQL UPSERT, and rename PDFs.'

    def handle(self, *args, **kwargs):
        input_dir = './ffs_input'
        output_dir = './ffs_output_new'
        sql_dir = './sql_output_new'
        ksei_file = 'KSEI_DATA_MAY_2026.txt'
        pefindo_file = 'PEFINDO_BOND_RATING_MAY_2026.pdf'
        kode_produk_file = 'Kode Produk.xlsx'
        prompts_dir = './mutualfund/ai/prompts'

        # 1. Inisialisasi Service Lama
        pefindo_svc = PefindoService(pefindo_file)
        ksei_svc = KseiService(ksei_file, kode_produk_file, pefindo_service=pefindo_svc)
        sql_svc = SQLService(sql_dir)
        rename_svc = RenameService(output_dir)
        pdf_svc = PDFService()

        # 2. Inisialisasi AI Extractor
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY tidak ditemukan!")
        ai_extractor = AIExtractor(api_key=api_key, prompts_dir=prompts_dir)

        available_prompts = [
            f.replace('.txt', '') for f in os.listdir(prompts_dir) if f.endswith('.txt')
        ]

        for filename in os.listdir(input_dir):
            if not filename.endswith('.pdf'): 
                continue
            
            filepath = os.path.join(input_dir, filename)
        
            try:
                raw_text = pdf_svc.extract_text(filepath)
                text = normalize_pdf_text(raw_text)
                text_lower = text.lower()
                mi_name = None
                
                # Deteksi MI menggunakan prompt yang sudah di-load
                for prompt_name in available_prompts:
                    if prompt_name.lower() in text_lower:
                        if len(prompt_name) <= 4:
                            mi_name = prompt_name.upper() 
                        else:
                            mi_name = prompt_name.title() 
                        break
                
                if not mi_name: 
                    self.stdout.write(self.style.WARNING(f"Lewati: {filename} (MI tidak dikenali)"))
                    continue

                self.stdout.write(f"Mengekstrak {filename} dengan AI (MI: {mi_name})...")
                
                # --- PROSES INTI AI ---
                ffs_data = ai_extractor.extract(text, mi_name)
                
                # SIMPAN KODE ISIN DARI AI SEBAGAI CADANGAN
                ai_extracted_code = ffs_data.get('productCode', '').strip()
                
                # --- ENRICHMENT KSEI & PEFINDO ---
                enriched_holdings = []
                for holding in ffs_data.get('topHoldings', []):
                    clean_name = holding.get('name', '')
                    pct = holding.get('percentage', 0.0)
                    
                    if clean_name and pct > 0:
                        enriched = ksei_svc.enrich_holding_data(clean_name, ffs_data.get('ffsDate', ''))
                        enriched['percentage'] = pct
                        enriched_holdings.append(enriched)
                ffs_data['topHoldings'] = enriched_holdings
                
                # --- MAPPING PRODUCT CODE & NAMA ---
                if ffs_data.get('productName'):
                    found_code, found_name = ksei_svc.match_product_code(ffs_data['productName'])
                    if found_code:
                        ffs_data['productCode'] = found_code
                        ffs_data['productName'] = found_name
                    elif ai_extracted_code: # Fallback kalau di Excel nggak ada
                        ffs_data['productCode'] = ai_extracted_code
                        self.stdout.write(self.style.WARNING(f"Produk tidak ada di Excel. Pakai ISIN AI: {ai_extracted_code}"))
                    else:
                        ffs_data['productCode'] = f"UNKNOWN_{mi_name.upper()}_{filename[:6].upper()}"
                else:
                    if ai_extracted_code:
                        ffs_data['productCode'] = ai_extracted_code
                    else:
                        ffs_data['productCode'] = f"UNKNOWN_{mi_name.upper()}_{filename[:6].upper()}"

                # --- RENAME FILE & GENERATE SQL ---
                rename_svc.copy_and_rename(filepath, ffs_data['productCode'], ffs_data['ffsPeriod'])
                sql_svc.add_query(mi_name, ffs_data)
                
                self.stdout.write(self.style.SUCCESS(f"Sukses memproses: {filename}"))
                
                time.sleep(4)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error memproses {filename}: {e}"))

        sql_svc.save_all(lambda msg: self.stdout.write(self.style.SUCCESS(msg)))