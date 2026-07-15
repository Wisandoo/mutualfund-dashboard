import os
import json
import pdfplumber
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Menjalankan eksperimen ekstraksi PDF pada berbagai Fund Fact Sheet (UOB, Syailendra, dll).'

    def handle(self, *args, **kwargs):
        # Tambahkan nama file PDF UOB dan Syailendra Anda di sini
        pdf_files = ["IB27 - (May_26).pdf", "FFS_SBOFA MEI 26.pdf"]
        base_output_dir = "./ffs_diagnostics"
        
        for pdf_path in pdf_files:
            self.stdout.write("\n" + "="*80)
            self.stdout.write(f" MENDIAGNOSIS: {pdf_path} ".center(80, '='))
            
            if not os.path.exists(pdf_path):
                self.stdout.write(self.style.ERROR(f"  [ERROR] File {pdf_path} tidak ditemukan. Dilewati."))
                continue

            # Buat folder khusus per FFS agar file dump tidak tercampur
            mi_name = pdf_path.split('.')[0]
            output_dir = os.path.join(base_output_dir, mi_name)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            full_text_standard = ""
            full_text_layout = ""
            full_words = []
            full_find_tables = []
            full_extract_tables = []

            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page_num, page in enumerate(pdf.pages, 1):
                        # 1. extract_text() standar
                        text_std = page.extract_text() or ""
                        full_text_standard += f"--- PAGE {page_num} ---\n{text_std}\n\n"

                        # 2. extract_text(layout=True)
                        text_layout = page.extract_text(layout=True) or ""
                        full_text_layout += f"--- PAGE {page_num} ---\n{text_layout}\n\n"

                        # 3. extract_words()
                        words = page.extract_words()
                        full_words.append({"page": page_num, "words": words})

                        # 4. find_tables()
                        tables_objs = page.find_tables()
                        bboxes = [t.bbox for t in tables_objs]
                        full_find_tables.append({"page": page_num, "table_bboxes": bboxes})

                        # 5. extract_tables()
                        tables = page.extract_tables()
                        full_extract_tables.append({"page": page_num, "tables": tables})

                # --- SAVE RAW OUTPUTS ---
                with open(os.path.join(output_dir, "1_extract_text.txt"), "w", encoding="utf-8") as f:
                    f.write(full_text_standard)

                with open(os.path.join(output_dir, "2_extract_layout.txt"), "w", encoding="utf-8") as f:
                    f.write(full_text_layout)

                with open(os.path.join(output_dir, "3_extract_words.json"), "w", encoding="utf-8") as f:
                    json.dump(full_words, f, indent=2, ensure_ascii=False)

                with open(os.path.join(output_dir, "4_find_tables.json"), "w", encoding="utf-8") as f:
                    json.dump(full_find_tables, f, indent=2, ensure_ascii=False)

                with open(os.path.join(output_dir, "5_extract_tables.json"), "w", encoding="utf-8") as f:
                    json.dump(full_extract_tables, f, indent=2, ensure_ascii=False)

                # --- PRINT HASIL KE TERMINAL ---
                self.stdout.write("\n>>> SAMPEL: extract_text(layout=True) <<<")
                sample_lay = full_text_layout.split('\n')[:20]
                self.stdout.write('\n'.join(sample_lay))

                self.stdout.write("\n>>> SAMPEL: find_tables() <<<")
                if full_find_tables and full_find_tables[0]["table_bboxes"]:
                    for i, bbox in enumerate(full_find_tables[0]["table_bboxes"]):
                        self.stdout.write(f"  Tabel {i+1} terdeteksi di: {bbox}")
                else:
                    self.stdout.write("  [KOSONG] Bounding box tabel tidak terdeteksi.")

                self.stdout.write("\n>>> SAMPEL: extract_tables() <<<")
                if full_extract_tables and full_extract_tables[0]["tables"]:
                    for i, table in enumerate(full_extract_tables[0]["tables"]):
                        self.stdout.write(f"\n  -- Tabel {i+1} --")
                        for j, row in enumerate(table[:5]): 
                            self.stdout.write(f"   Baris {j+1}: {row}")
                else:
                    self.stdout.write("  [KOSONG] Data matriks tabel gagal diekstrak.")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  [ERROR] Gagal memproses {pdf_path}: {e}"))
                
        self.stdout.write("\n" + "="*80)
        self.stdout.write(" SELURUH PROSES DIAGNOSTIK SELESAI ".center(80))
        self.stdout.write("="*80 + "\n")