import os
import json
import pdfplumber
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Menjalankan eksperimen ekstraksi PDF menggunakan berbagai metode pdfplumber.'

    def handle(self, *args, **kwargs):
        pdf_path = "PEFINDO_BOND_RATING_MAY_2026.pdf"
        output_dir = "./pdf_diagnostics"
        
        # Cek ketersediaan file PDF
        if not os.path.exists(pdf_path):
            self.stdout.write(self.style.ERROR(f"File {pdf_path} tidak ditemukan! Pastikan file berada di root directory."))
            return

        # Buat folder output jika belum ada
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        stats = {
            "total_pages": 0,
            "total_words": 0,
            "total_tables": 0,
            "lines_standard": 0,
            "lines_layout": 0
        }

        # Penampung data mentah untuk di-dump ke file
        full_text_standard = ""
        full_text_layout = ""
        full_words = []
        full_tables = []
        full_find_tables = []

        self.stdout.write("Memproses PDF, silakan tunggu...")

        try:
            with pdfplumber.open(pdf_path) as pdf:
                stats["total_pages"] = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages, 1):
                    # 1. Evaluasi extract_text() standar
                    text_std = page.extract_text() or ""
                    full_text_standard += f"--- PAGE {page_num} ---\n{text_std}\n\n"
                    stats["lines_standard"] += len(text_std.split('\n'))

                    # 2. Evaluasi extract_text(layout=True)
                    text_layout = page.extract_text(layout=True) or ""
                    full_text_layout += f"--- PAGE {page_num} ---\n{text_layout}\n\n"
                    stats["lines_layout"] += len(text_layout.split('\n'))

                    # 3. Evaluasi extract_words()
                    words = page.extract_words()
                    stats["total_words"] += len(words)
                    full_words.append({"page": page_num, "words": words})

                    # 4. Evaluasi find_tables()
                    tables_objs = page.find_tables()
                    bboxes = [t.bbox for t in tables_objs]
                    full_find_tables.append({"page": page_num, "table_bboxes": bboxes})

                    # 5. Evaluasi extract_tables()
                    tables = page.extract_tables()
                    stats["total_tables"] += len(tables)
                    full_tables.append({"page": page_num, "tables": tables})

            # ==========================================
            # SAVE RAW OUTPUTS UNTUK INSPEKSI MANUAL
            # ==========================================
            with open(os.path.join(output_dir, "1_extract_text.txt"), "w", encoding="utf-8") as f:
                f.write(full_text_standard)

            with open(os.path.join(output_dir, "2_extract_text_layout.txt"), "w", encoding="utf-8") as f:
                f.write(full_text_layout)

            with open(os.path.join(output_dir, "3_extract_words.json"), "w", encoding="utf-8") as f:
                json.dump(full_words, f, indent=2, ensure_ascii=False)

            with open(os.path.join(output_dir, "4_find_tables.json"), "w", encoding="utf-8") as f:
                json.dump(full_find_tables, f, indent=2, ensure_ascii=False)

            with open(os.path.join(output_dir, "5_extract_tables.json"), "w", encoding="utf-8") as f:
                json.dump(full_tables, f, indent=2, ensure_ascii=False)

            # ==========================================
            # PRINT STATISTIK & SAMPEL 10 RECORD KE TERMINAL
            # ==========================================
            self.stdout.write("\n" + "="*80)
            self.stdout.write(" LAPORAN EKSPERIMEN METODE PDFPLUMBER ".center(80))
            self.stdout.write("="*80)
            self.stdout.write(f"Total Halaman (Pages)         : {stats['total_pages']}")
            self.stdout.write(f"Total Teks Standard (Lines)   : {stats['lines_standard']}")
            self.stdout.write(f"Total Teks Layout (Lines)     : {stats['lines_layout']}")
            self.stdout.write(f"Total Kata (Words)            : {stats['total_words']}")
            self.stdout.write(f"Total Tabel Terdeteksi        : {stats['total_tables']}")
            self.stdout.write("-" * 80)

            self.stdout.write("\n>>> SAMPEL: extract_text() <<<")
            sample_std = full_text_standard.split('\n')[1:11] 
            self.stdout.write('\n'.join(sample_std))

            self.stdout.write("\n>>> SAMPEL: extract_text(layout=True) <<<")
            sample_lay = full_text_layout.split('\n')[1:11]
            self.stdout.write('\n'.join(sample_lay))

            self.stdout.write("\n>>> SAMPEL: extract_words() <<<")
            if full_words and full_words[0]["words"]:
                for i, w in enumerate(full_words[0]["words"][:10]):
                    self.stdout.write(f"[{i+1}] Text: '{w['text']:<15}' | Coord: (x0:{w['x0']:>6.2f}, top:{w['top']:>6.2f}, bottom:{w['bottom']:>6.2f})")

            self.stdout.write("\n>>> SAMPEL: find_tables() (Bounding Box) <<<")
            if full_find_tables and full_find_tables[0]["table_bboxes"]:
                for i, bbox in enumerate(full_find_tables[0]["table_bboxes"][:10]):
                    self.stdout.write(f"Table {i+1} Bounding Box: {bbox}")
            else:
                self.stdout.write("[KOSONG] Tidak ada tabel yang terdeteksi sebagai Table Object.")

            self.stdout.write("\n>>> SAMPEL: extract_tables() (Row Cells) <<<")
            if full_tables and full_tables[0]["tables"]:
                for i, row in enumerate(full_tables[0]["tables"][0][:10]):
                    self.stdout.write(f"Row {i+1}: {row}")
            else:
                self.stdout.write("[KOSONG] Tidak ada baris/sel data tabel yang berhasil diekstrak.")
            
            self.stdout.write("="*80)
            self.stdout.write(f"Semua file raw telah di-dump untuk inspeksi di folder: '{output_dir}'")
            self.stdout.write("="*80 + "\n")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Kritis! Error saat membaca PDF: {e}"))