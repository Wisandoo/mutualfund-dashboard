import os
import pdfplumber
from django.core.management.base import BaseCommand
from mutualfund.parsers.sucorinvest import SucorinvestParser
from mutualfund.services.ksei_service import KseiService

class Command(BaseCommand):
    help = 'Utility diagnostic khusus untuk melacak kegagalan produk Sucorinvest.'

    def handle(self, *args, **kwargs):
        input_dir = './ffs_input'
        output_file = 'debug_sucorinvest.txt'
        ksei_file = 'KSEI_DATA_MAY_2026.txt'
        kode_produk_file = 'Kode Produk.xlsx'
        ksei_service = KseiService(ksei_file, kode_produk_file)
        
        # Masukkan service ke parser
        parser = SucorinvestParser(ksei_service)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            if not os.path.exists(input_dir):
                self.stdout.write(self.style.ERROR(f"Folder {input_dir} tidak ditemukan."))
                return

            pdf_files = [file for file in os.listdir(input_dir) if file.lower().endswith('.pdf')]
            
            for filename in pdf_files:
                filepath = os.path.join(input_dir, filename)
                
                try:
                    with pdfplumber.open(filepath) as pdf:
                        first_page = pdf.pages[0].extract_text() or ""
                        if "sucorinvest" not in first_page.lower():
                            continue

                    text = ""
                    with pdfplumber.open(filepath) as pdf:
                        for page in pdf.pages:
                            extracted = page.extract_text()
                            if extracted:
                                text += extracted + "\n"
                    
                    # Normalisasi spasi seperti biasa
                    text_clean = text.replace("\xa0", " ")
                    
                    # Gunakan parser yang sudah ada tanpa diubah
                    ffs_data = parser.parse(text_clean)
                    
                    p_name = ffs_data.get('productName', '')
                    p_date = ffs_data.get('ffsDate', '')
                    p_aum = ffs_data.get('aum', 0)
                    p_type = ffs_data.get('mfType', '')
                    p_obj = ffs_data.get('investmentObjective', '')
                    alloc_count = len(ffs_data.get('portfolioAllocations', []))
                    hold_count = len(ffs_data.get('topHoldings', []))

                    # Pengecekan field yang hilang
                    missing_fields = []
                    if not p_name: missing_fields.append("Product Name")
                    if not p_date: missing_fields.append("Date")
                    if not p_aum: missing_fields.append("AUM")
                    if alloc_count == 0: missing_fields.append("Allocation")
                    if hold_count == 0: missing_fields.append("Holding")

                    f.write("====================================================\n")
                    f.write(f"File : {filename}\n")
                    f.write(f"Text Length : {len(text_clean)} karakter\n\n")
                    
                    f.write(f"Product Name : {p_name}\n")
                    f.write(f"Date : {p_date}\n")
                    f.write(f"AUM : {p_aum}\n")
                    f.write(f"Fund Type : {p_type}\n")
                    f.write(f"Objective : {'Terisi' if p_obj else 'KOSONG'}\n")
                    f.write(f"Allocation Count : {alloc_count}\n")
                    f.write(f"Holding Count : {hold_count}\n\n")
                    
                    if not missing_fields:
                        f.write("READY TO SAVE : YES\n")
                    else:
                        f.write("READY TO SAVE : NO\n")
                        f.write(f"Field Kosong : {', '.join(missing_fields)}\n")
                    f.write("====================================================\n\n")
                    
                    # LOGIKA DB LOOKUP
                    if p_name:
                        is_found = False # Ganti ke True jika logic DB asli Anda mengembalikan nilai cocok
                        
                        if not is_found:
                            f.write(">>> DB CHECK: PRODUCT NOT FOUND\n")
                            f.write(f">>> Parsed Name : '{p_name}'\n\n")

                except Exception as e:
                    f.write(f"Error memproses {filename}: {str(e)}\n\n")
                    
        self.stdout.write(self.style.SUCCESS(f"Selesai! Buka file '{output_file}' untuk melihat hasil diagnostik."))