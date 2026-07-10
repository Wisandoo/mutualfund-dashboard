import os
from django.core.management.base import BaseCommand
from mutualfund.services.pdf_service import PDFService
from mutualfund.services.sql_service import SQLService
from mutualfund.services.rename_service import RenameService
from mutualfund.services.ksei_service import KseiService
from mutualfund.parsers.uob import UOBParser
from mutualfund.parsers.syailendra import SyailendraParser
from mutualfund.parsers.sucorinvest import SucorinvestParser
from mutualfund.utils import normalize_pdf_text

class Command(BaseCommand):
    help = 'Modular: Extract FFS data, generate SQL, and rename PDFs.'

    def handle(self, *args, **kwargs):
        input_dir = './ffs_input'
        output_dir = './ffs_output'
        sql_dir = './sql_output'
        ksei_file = 'KSEI_DATA_MAY_2026.txt'
        kode_produk_file = 'Kode Produk.xlsx'

        ksei_svc = KseiService(ksei_file, kode_produk_file)
        sql_svc = SQLService(sql_dir)
        rename_svc = RenameService(output_dir)
        pdf_svc = PDFService()

        parsers = {
            "UOB": UOBParser(ksei_svc),
            "Syailendra": SyailendraParser(ksei_svc),
            "Sucorinvest": SucorinvestParser(ksei_svc)
        }

        for filename in os.listdir(input_dir):
            if not filename.endswith('.pdf'): 
                continue
            
            filepath = os.path.join(input_dir, filename)
        
            try:
                raw_text = pdf_svc.extract_text(filepath)
                text = normalize_pdf_text(raw_text)
                text_lower = text.lower()

                # Deteksi MI
                mi_name = None
                if "uob" in text_lower or "uobam" in text_lower: 
                    mi_name = "UOB"
                elif "sucor" in text_lower: 
                    mi_name = "Sucorinvest"
                elif "syailendra" in text_lower: 
                    mi_name = "Syailendra"
                
                if not mi_name: 
                    self.stdout.write(self.style.WARNING(f"Lewati: {filename} (MI tidak dikenali)"))
                    continue

                parser = parsers[mi_name]
                ffs_data = parser.parse(text)
                
                if ffs_data.get('productName'):
                    found_code, found_name = ksei_svc.match_product_code(ffs_data['productName'])
                    if found_code:
                        ffs_data['productCode'] = found_code
                        ffs_data['productName'] = found_name
                    else:
                        ffs_data['productCode'] = f"UNKNOWN_{mi_name.upper()}_{filename[:6].upper()}"
                else:
                    ffs_data['productCode'] = f"UNKNOWN_{mi_name.upper()}_{filename[:6].upper()}"

                rename_svc.copy_and_rename(filepath, ffs_data['productCode'], ffs_data['ffsPeriod'])
                sql_svc.add_query(mi_name, ffs_data)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error memproses {filename}: {e}"))

        # Output final
        sql_svc.save_all(lambda msg: self.stdout.write(self.style.SUCCESS(msg)))