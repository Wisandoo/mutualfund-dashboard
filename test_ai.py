import os
import json
import pdfplumber
from mutualfund.ai.extractor import AIExtractor
from mutualfund.pipeline import FFSDataPipeline

def main():
    pdf_path = "ffs_input/UNION - (May_26).pdf" 
    mi_name = "uob" 
    api_key_gue = "AQ.Ab8RN6Kfpg5qW7Y0NXAikhkGKQTq4IZzObBrgrUvRFsvtKMNkA" 
    
    if not os.path.exists(pdf_path):
        print(f"File PDF {pdf_path} gak ketemu, Bro.")
        return

    # --- TAHAP 1: EKSTRAKSI AI ---
    print(f"Membaca isi PDF: {pdf_path}...")
    pdf_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            teks = page.extract_text()
            if teks:
                pdf_text += teks + "\n"

    print(f"Mengirim teks ke AI untuk MI: {mi_name.upper()}...")
    extractor = AIExtractor(api_key=api_key_gue, prompts_dir="mutualfund/ai/prompts") 
    hasil_json = extractor.extract(pdf_text, mi_name)

    print("\n=== HASIL EKSTRAKSI AI ===")
    print(json.dumps(hasil_json, indent=4))

    # --- TAHAP 2: SQL & RENAME FILE ---
    print("\n=== MENJALANKAN DATA PIPELINE ===")
    pipeline = FFSDataPipeline(output_dir="ffs_output_new")

    # 1. Generate SQL
    sql_statement = pipeline.generate_sql(data=hasil_json)
    print("\n[SQL GENERATED]")
    print(sql_statement)

    # 2. Rename & Pindah File
    new_file_path = pipeline.rename_and_move_pdf(pdf_path, hasil_json)
    if new_file_path:
        print(f"\n[FILE RENAMED] File berhasil disalin ke: {new_file_path}")

if __name__ == "__main__":
    main()