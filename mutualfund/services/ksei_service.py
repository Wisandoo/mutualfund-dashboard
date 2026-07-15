import pandas as pd
import re

class KseiService:
    def __init__(self, ksei_file, kode_produk_file, pefindo_service=None):
        self.df_ksei = pd.DataFrame()
        self.df_kode = pd.DataFrame()
        self.pefindo_service = pefindo_service
        self._load_ksei(ksei_file)
        self._load_kode(kode_produk_file)

    def _load_ksei(self, filepath):
        try:
            df = pd.read_csv(filepath, sep='|', on_bad_lines='skip')
            df.columns = df.columns.str.strip()
            df['Description'] = df['Description'].fillna('').astype(str)
            df['desc_len'] = df['Description'].str.len()
            self.df_ksei = df.sort_values(by='desc_len', ascending=False)
        except Exception as e:
            print(f"Gagal memuat {filepath}: {e}")

    def _load_kode(self, filepath):
        try:
            df = pd.read_excel(filepath)
            df.columns = df.columns.str.strip().str.lower()
            self.df_kode = df
        except Exception as e:
            print(f"Gagal memuat {filepath}: {e}")

    def match_product_code(self, ffs_name):
        if self.df_kode.empty or not ffs_name:
            return None, None
        
        def clean_for_match(name_str):
            n = str(name_str).lower()
            for w in ['reksa dana', 'pt.', 'asset management','indeks', 'syariah']:
                n = n.replace(w, '')
            n = re.sub(r'\s+', ' ', n).strip()
            return n

        pdf_name_clean = clean_for_match(ffs_name)
        
        found_code = None
        found_name = None
        max_len = 0
        
        for _, row in self.df_kode.iterrows():
            excel_name_raw = str(row['nama produk']).strip()
            excel_name_clean = clean_for_match(excel_name_raw)

            if excel_name_clean == pdf_name_clean:
                return str(row['kode produk']), excel_name_raw
            
        if (
            excel_name_clean in pdf_name_clean or
            pdf_name_clean in excel_name_clean
        ):
            if len(excel_name_clean) > max_len:
                max_len = len(excel_name_clean)
                found_code = str(row['kode produk'])
                found_name = excel_name_raw

        return found_code, found_name

    def enrich_holding_data(self, messy_holding_name, ffs_date_str):
        messy_name = str(messy_holding_name).upper().strip()
        best_match_row = None
        exact_name = messy_name
        
        if not self.df_ksei.empty:
            match_code = self.df_ksei[self.df_ksei['Code'].str.upper() == messy_name]
            if not match_code.empty:
                best_match_row = match_code.iloc[0]
            else:
                # Helper untuk mensterilkan kata kunci (Jaccard Index KSEI)
                def get_clean_tokens(text):
                    t = str(text).upper()
                    t = re.sub(r'\b(PT|TBK|PERSERO|PERUSAHAAN PERSEROAN|OBLIGASI|SUKUK|BERKELANJUTAN|TAHAP|TAHUN|SERI)\b', '', t)
                    t = re.sub(r'[^A-Z0-9\s]', ' ', t)
                    return set(t.split())

                q_tokens = get_clean_tokens(messy_name)
                highest_score = 0.0
                
                for _, row in self.df_ksei.iterrows():
                    desc = str(row['Description']).upper()
                    
                    # 1. EXACT/SUBSTRING MATCH YANG AMAN
                    desc_sub = re.sub(r'\b(PT|TBK|PERSERO|PERUSAHAAN PERSEROAN)\b', '', desc).strip()
                    desc_sub = re.sub(r'\s+', ' ', desc_sub)
                    
                    if desc_sub in messy_name and len(desc_sub) > 10:
                        best_match_row = row
                        break
                        
                    # 2. JACCARD SIMILARITY MATCH
                    p_tokens = get_clean_tokens(desc)
                    if not p_tokens or not q_tokens: 
                        continue
                        
                    intersection = q_tokens.intersection(p_tokens)
                    union = q_tokens.union(p_tokens)
                    score = len(intersection) / len(union)
                    
                    if score > highest_score and score > 0.45:
                        highest_score = score
                        best_match_row = row

        holding_data = {"name": exact_name, "percentage": 0.0}

        if best_match_row is not None:
            ticker = str(best_match_row['Code'])
            final_name = str(best_match_row['Description']).upper()
            final_name = re.sub(r'\b(PT|TBK|PERSERO|PERUSAHAAN PERSEROAN)\b', '', final_name)
            final_name = re.sub(r'[\(\)\,\.]', ' ', final_name)
            final_name = re.sub(r'\s+', ' ', final_name).strip()
            
            holding_data["name"] = final_name
            
            holding_data.update({
                "code": ticker,
                "url": f"https://www.idx.co.id/id/perusahaan-tercatat/profil-perusahaan-tercatat/{ticker}",
                "type": str(best_match_row['Type']),
                "sector": str(best_match_row['Sector']),
                "asOfDate": ffs_date_str,
                "issuer": str(best_match_row['Issuer']),
                "interest": float(best_match_row['Interest']) if pd.notna(best_match_row['Interest']) and str(best_match_row['Interest']).strip() else None,
                "couponFrequency": str(best_match_row['Interest Freq']).strip() if pd.notna(best_match_row['Interest Freq']) else None,
                "closingPrice": float(best_match_row['Closing Price']) if pd.notna(best_match_row['Closing Price']) else 0.0,
                "priceDate": ffs_date_str,
                "tvUrl": f"https://www.tradingview.com/symbols/IDX-{ticker}/"
            })

        # Pastikan key Pefindo default terisi jika tidak ada Pefindo match
        holding_data["rating"] = None
        holding_data["maturityDate"] = None
        holding_data.setdefault("couponFrequency", None)

        # Triggers Pefindo
        is_bond = any(kw in holding_data["name"].upper() for kw in ["OBLIGASI", "SUKUK", "MTN", "SURAT", "SBSN", "FR", "PBS"])
        
        if is_bond and getattr(self, 'pefindo_service', None):
            pefindo_match = self.pefindo_service.find_bond(holding_data["name"])
            if pefindo_match is not None:
                holding_data["rating"] = str(pefindo_match["rating"])
                holding_data["maturityDate"] = str(pefindo_match["maturity_date"])
                holding_data["couponFrequency"] = str(pefindo_match["coupon_frequency"])
            
        return holding_data