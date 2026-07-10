import os
import re
import json
import shutil
import pandas as pd
import pdfplumber
from datetime import datetime
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Extract FFS data from UOB, Sucorinvest, and Syailendra, generate SQL, and rename PDFs.'

    def handle(self, *args, **kwargs):
        input_dir = './ffs_input'
        output_dir = './ffs_output'
        sql_dir = './sql_output'

        for d in [input_dir, output_dir, sql_dir]:
            os.makedirs(d, exist_ok=True)

        ksei_file = 'KSEI_DATA_MAY_2026.txt'
        kode_produk_file = 'Kode Produk.xlsx'

        try:
            df_ksei = pd.read_csv(ksei_file, sep='|', on_bad_lines='skip')
            df_ksei.columns = df_ksei.columns.str.strip()
            if not df_ksei.empty:
                df_ksei['Description'] = df_ksei['Description'].fillna('').astype(str)
                df_ksei['desc_len'] = df_ksei['Description'].str.len()
                df_ksei = df_ksei.sort_values(by='desc_len', ascending=False)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Gagal memuat {ksei_file}: {e}"))
            df_ksei = pd.DataFrame()

        try:
            df_kode = pd.read_excel(kode_produk_file)
            df_kode.columns = df_kode.columns.str.strip().str.lower()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Gagal memuat {kode_produk_file}: {e}"))
            df_kode = pd.DataFrame()

        def parse_aum(aum_str):
            aum_str = str(aum_str).lower().replace('rp', '').replace('idr', '').replace('usd', '').replace('$', '').replace(',', '.').strip()
            multiplier = 1
            
            # Deteksi keyword dengan regex agar tahan terhadap teks dobel (misal: "mmiillyyaarr")
            if re.search(r'(triliun|t|bili|bio)', aum_str):
                multiplier = 1e12
            elif re.search(r'(milyar|miliar|m|bil|b)', aum_str):
                multiplier = 1e9
            elif re.search(r'(juta|million|jt)', aum_str):
                multiplier = 1e6
            
            aum_clean = re.sub(r'[^\d\.]', '', aum_str)
            
            # Hapus multiple dots sisa shadow text PDF (contoh: '376..64' -> '376.64')
            aum_clean = re.sub(r'\.+', '.', aum_clean)
            
            parts = aum_clean.split('.')
            if len(parts) > 2:
                aum_clean = aum_clean.replace('.', '', len(parts) - 2)
            try:
                return float(aum_clean) * multiplier
            except:
                return 0.0

        def get_month_en(indonesian_month):
            months = {"januari": "JAN", "februari": "FEB", "maret": "MAR", "april": "APR", "mei": "MAY", "mel": "MAY", "juni": "JUN", "juli": "JUL", "agustus": "AUG", "september": "SEP", "oktober": "OCT", "november": "NOV", "desember": "DEC"}
            return months.get(indonesian_month.lower(), "JAN")

        def enrich_holding_data(messy_holding_name, ffs_date_str):
            """Fungsi Cerdas: Mengekstrak nama emiten bersih dari teks yang berantakan"""
            messy_name = messy_holding_name.upper()
            best_match_row = None
            exact_name = messy_holding_name.strip()
            
            if not df_ksei.empty:
                # 1. REVERSE MATCHING: Cari apakah nama KSEI ada di dalam teks yang berantakan
                for _, row in df_ksei.iterrows():
                    desc = str(row['Description']).upper()
                    
                    desc_clean = re.sub(r'\b(PT|TBK|PERSERO|PERUSAHAAN PERSEROAN|SERI\s+[A-Z])\b', '', desc, flags=re.IGNORECASE)

                    desc_clean = re.sub(r'[\(\)\,\.]', ' ', desc_clean)

                    desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()

                    if desc_clean in messy_name and len(desc_clean) > 3:
                        best_match_row = row
                        exact_name = desc_clean
                        break

                if best_match_row is None:
                    match = df_ksei[df_ksei['Code'].astype(str).str.strip().str.upper() == exact_name.upper()]
                    
                    if match.empty:
                        match = df_ksei[df_ksei['Code'].astype(str).str.contains(exact_name, case=False, na=False, regex=False)]
                        
                    if match.empty:
                        match = df_ksei[df_ksei['Description'].astype(str).str.contains(exact_name, case=False, na=False, regex=False)]
                        
                    if not match.empty:
                        best_match_row = match.iloc[0]
                        exact_name = str(best_match_row['Description']).upper()
                        exact_name = re.sub(r'\b(PT|TBK|PERSERO|PERUSAHAAN PERSEROAN)\b', '', exact_name, flags=re.IGNORECASE)
                        exact_name = re.sub(r'[\(\)\,\.]', ' ', exact_name)
                        exact_name = re.sub(r'\s+', ' ', exact_name).strip()

            holding_data = {"name": exact_name, "percentage": 0.0}

            if best_match_row is not None:
                ticker = str(best_match_row['Code'])
                holding_data.update({
                    "code": ticker,
                    "url": f"https://www.idx.co.id/id/perusahaan-tercatat/profil-perusahaan-tercatat/{ticker}",
                    "type": str(best_match_row['Type']),
                    "sector": str(best_match_row['Sector']),
                    "asOfDate": ffs_date_str,
                    "issuer": str(best_match_row['Issuer']),
                    "closingPrice": float(best_match_row['Closing Price']) if pd.notna(best_match_row['Closing Price']) else 0.0,
                    "priceDate": ffs_date_str,
                    "tvUrl": f"https://www.tradingview.com/symbols/IDX-{ticker}/"
                })
            else:
                holding_data["code"] = exact_name
                
            return holding_data

        sql_queries = {"UOB": [], "Sucorinvest": [], "Syailendra": []}

        for filename in os.listdir(input_dir):
            if not filename.endswith('.pdf'): continue
            filepath = os.path.join(input_dir, filename)
            text = ""
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"

            mi_name = ""
            text_lower = text.lower()
            text_clean = re.sub(r'\s+', ' ', text)

            if "uob" in text_lower or "uobam" in text_lower: mi_name = "UOB"
            elif "syailendra" in text_lower: mi_name = "Syailendra"
            else: continue

            ffs_data = {
                "ffsDate": "", "launchDate": "", "aum": 0.0, "totalAum": 0, "currency": "IDR",
                "topHoldings": [], "portfolioAllocations": [],
                "investmentObjective": "", "mfType": "", "productCode": "", 
                "productName": "", "ffsPeriod": ""
            }

            # ----------------- PARSING UOB -----------------
            if mi_name == "UOB":
                prod_match = re.search(r'UOBAM\s+([A-Za-z0-9\s\-\_]+)', text)
                if prod_match: ffs_data['productName'] = prod_match.group(0).strip()
                
                date_match = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', text)
                if date_match:
                    day, month, year = date_match.groups()
                    ffs_data['ffsDate'] = f"{year}-{get_month_en(month)}-{day.zfill(2)}"
                    ffs_data['ffsPeriod'] = f"{get_month_en(month)}_{year}"

                aum_match = re.search(r'(?:Total Nilai Aktiva Bersih|Total AUM)\s*[:\n]*\s*Rp\s*([\d\.\,]+)', text, re.IGNORECASE)
                if aum_match: 
                    aum_raw = aum_match.group(1).replace(',', '')
                    ffs_data['aum'] = parse_aum(aum_raw)
                    ffs_data['totalAum'] = int(ffs_data['aum'])

                jenis_match = re.search(r'Reksa Dana (Indeks|Campuran|Saham|Pasar Uang|Pendapatan Tetap)', text, re.IGNORECASE)
                if jenis_match: ffs_data['mfType'] = jenis_match.group(1).upper()
                else: ffs_data['mfType'] = "CAMPURAN"

                try:
                    portofolio_chunk = text.split("Portofolio 10 Terbesar")[1].split("Kinerja")[0]
                    matches = re.findall(r'(.+?)\s+([\d\.,]+)%', portofolio_chunk)
                    
                    count = 0
                    for name_raw, pct in matches:
                        messy_str = name_raw.strip()
                        if len(messy_str) > 3 and count < 10:
                            pct_float = float(pct.replace(',', '.'))
                            enriched = enrich_holding_data(messy_str, ffs_data['ffsDate'])
                            
                            if enriched.get('code') != enriched['name']:
                                enriched['percentage'] = pct_float
                                ffs_data['topHoldings'].append(enriched)
                                count += 1
                except Exception:
                    pass

            # ----------------- PARSING SYAILENDRA -----------------
            elif mi_name == "Syailendra":
                prod_match = re.search(r'REKSA DANA\s+([A-Za-z0-9\s\-]+)', text, re.IGNORECASE)
                if prod_match:
                    clean_name = prod_match.group(1).split('\n')[0].strip()
                    ffs_data['productName'] = clean_name
                
                aum_match = re.search(r'Total Nilai Aktiva Bersih\s*Rp\s*([\d\.,]+\s*(?:triliun|miliar|milyar))', text, re.IGNORECASE)
                if aum_match: 
                    ffs_data['aum'] = parse_aum(aum_match.group(1))
                    ffs_data['totalAum'] = int(ffs_data['aum'])

                date_match = re.search(r'(\d{2})/([A-Za-z]+)/(\d{4})', text)
                if date_match:
                    day, month, year = date_match.groups()
                    ffs_data['ffsPeriod'] = f"{month.upper()}_{year}"
                    ffs_data['ffsDate'] = f"{year}-05-29"
                
                text_intro = text[:500]
                if "Pasar Uang" in text_intro: ffs_data['mfType'] = "PASAR UANG"
                elif "Ekuitas" in text_intro: ffs_data['mfType'] = "EKUITAS"
                elif "Pendapatan Tetap" in text_intro: ffs_data['mfType'] = "PENDAPATAN TETAP"
                elif "Indeks" in text_intro: ffs_data['mfType'] = "INDEKS"
                else: ffs_data['mfType'] = "CAMPURAN"

                holdings_match = re.findall(r'\d+\.\s+([A-Z0-9\s]+?)\s+([\d\.,]+)%', text)
                for code, pct in holdings_match:
                    code_clean = code.strip()
                    pct_float = float(pct.replace(',', '.'))
                    enriched = enrich_holding_data(code_clean, ffs_data['ffsDate'])
                    enriched['percentage'] = pct_float
                    ffs_data['topHoldings'].append(enriched)

            # ----------------- PENCUCOKAN KODE PRODUK & GENERATE SQL -----------------
            if not df_kode.empty and ffs_data['productName']:
                found_code = None
                found_name = None
                max_len = 0 
                
                def clean_for_match(name_str):
                    n = str(name_str).lower()
                    for w in ['reksa dana', 'syariah', 'kelas a', 'kelas b', 'kelas c', 'fund']:
                        n = n.replace(w, '')
                    return re.sub(r'\s+', ' ', n).strip()

                pdf_name_clean = clean_for_match(ffs_data['productName'])
                
                for _, row in df_kode.iterrows():
                    excel_name_raw = str(row['nama produk']).strip()
                    excel_name_clean = clean_for_match(excel_name_raw)
                    
                    if excel_name_clean in pdf_name_clean or pdf_name_clean in excel_name_clean:
                        if len(excel_name_clean) > max_len:
                            max_len = len(excel_name_clean)
                            found_code = str(row['kode produk'])
                            found_name = excel_name_raw
                            
                if found_code:
                    ffs_data['productCode'] = found_code
                    ffs_data['productName'] = found_name 
                else:
                    ffs_data['productCode'] = f"UNKNOWN_{mi_name.upper()}_{filename[:6].upper()}"
            else:
                ffs_data['productCode'] = f"UNKNOWN_{mi_name.upper()}_{filename[:6].upper()}"

            # Rename File PDF
            new_pdf_name = f"{ffs_data['productCode']}_FS_{ffs_data['ffsPeriod']}.pdf"
            new_pdf_path = os.path.join(output_dir, new_pdf_name)
            
            try:
                shutil.copy2(filepath, new_pdf_path)
            except Exception:
                pass

            valid_sql_date = ffs_data['ffsDate'] if len(ffs_data['ffsDate']) == 10 else "2026-06-30" 
            json_data_str = json.dumps(ffs_data, ensure_ascii=False).replace("'", "''")
            
            sql = f"""INSERT INTO mutualfund_ffs (product_code, ffs_date, data, aum, created_datetime) 
                    VALUES ('{ffs_data['productCode']}', '{valid_sql_date}', '{json_data_str}', '{ffs_data['totalAum']}', now()) 
                    ON DUPLICATE KEY UPDATE data = VALUES(data), aum = VALUES(aum), latest = 1, created_datetime = now();\n"""
            sql_queries[mi_name].append(sql)

        for mi, queries in sql_queries.items():
            if queries:
                with open(os.path.join(sql_dir, f"{mi}_insert.sql"), 'w', encoding='utf-8') as f:
                    f.write("\n".join(queries))
                self.stdout.write(self.style.SUCCESS(f"Berhasil membuat SQL untuk {mi}"))