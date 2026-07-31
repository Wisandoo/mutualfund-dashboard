import os
import shutil
import json
import pandas as pd

class FFSDataPipeline:
    def __init__(self, output_dir="ffs_output_new", excel_path="Kode Produk.xlsx"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        # Load mapping produk dari Excel ke memory (Dictionary)
        self.product_mapping = {}
        if os.path.exists(excel_path):
            df = pd.read_excel(excel_path)
            # Membersihkan spasi di awal/akhir nama produk agar matching lebih akurat
            df['Nama produk'] = df['Nama produk'].str.strip()
            self.product_mapping = dict(zip(df['Nama produk'], df['Kode Produk']))
            print(f"[INFO] Berhasil memuat {len(self.product_mapping)} mapping dari {excel_path}")
        else:
            print(f"[WARNING] File {excel_path} tidak ditemukan di root folder!")

    def _get_internal_code(self, product_name, ai_default_code):
        """Mencari kode internal berdasarkan nama produk."""
        clean_name = product_name.strip()
        return self.product_mapping.get(clean_name, ai_default_code)

    def generate_sql(self, data):
        """Menghasilkan SQL UPSERT persis seperti parser lama."""
        
        # 1. MAPPING PRODUCT CODE
        ai_code = data.get("productCode", "")
        p_name = data.get("productName", "")
        
        # Ganti ISIN dari AI dengan Kode Internal dari Excel
        internal_code = self._get_internal_code(p_name, ai_code)
        
        # Update JSON datanya agar kode produk di dalam JSON ikut berubah
        data["productCode"] = internal_code
        
        # 2. SIAPKAN VARIABEL UNTUK SQL
        f_date = data.get("ffsDate", "")
        aum = data.get("totalAum", 0)
        
        # Bungkus ulang seluruh JSON menjadi string, dan amankan petik tunggal
        json_data = json.dumps(data).replace("'", "''")

        # 3. RAKIT QUERY (Menggunakan skema UPSERT lama)
        sql = f"""
INSERT INTO mutualfund_ffs (product_code, ffs_date, data, aum, created_datetime) 
VALUES ('{internal_code}', '{f_date}', '{json_data}', '{aum}', now()) 
ON DUPLICATE KEY UPDATE data = VALUES(data), aum = VALUES(aum), latest = 1, created_datetime = now();
        """.strip()
        
        return sql

    def rename_and_move_pdf(self, original_pdf_path, data):
        """Mengubah nama file sesuai format [product_code]_FS_[MONTH]_[YEAR].pdf"""
        
        # Gunakan productCode yang sudah di-mapping
        product_code = data.get("productCode", "UNKNOWN")
        period = data.get("ffsPeriod", "UNKNOWN")
        
        new_filename = f"{product_code}_FS_{period}.pdf"
        new_pdf_path = os.path.join(self.output_dir, new_filename)
        
        try:
            shutil.copy2(original_pdf_path, new_pdf_path)
            return new_pdf_path
        except Exception as e:
            print(f"[ERROR] Gagal memindahkan/rename file PDF: {e}")
            return None