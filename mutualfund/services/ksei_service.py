import pandas as pd
import re

class KseiService:
    def __init__(self, ksei_file, kode_produk_file):
        self.df_ksei = pd.DataFrame()
        self.df_kode = pd.DataFrame()
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
        for _, row in self.df_kode.iterrows():
            excel_name_raw = str(row['nama produk']).strip()
            excel_name_clean = clean_for_match(excel_name_raw)

            if excel_name_clean == pdf_name_clean:
                return str(row['kode produk']), excel_name_raw

        return None, None

    def enrich_holding_data(self, messy_holding_name, ffs_date_str):
        messy_name = messy_holding_name.upper()
        best_match_row = None
        exact_name = messy_holding_name.strip()
        
        if not self.df_ksei.empty:
            for _, row in self.df_ksei.iterrows():
                desc = str(row['Description']).upper()
                desc_clean = re.sub(r'\b(PT|TBK|PERSERO|PERUSAHAAN PERSEROAN|SERI\s+[A-Z])\b', '', desc, flags=re.IGNORECASE)
                desc_clean = re.sub(r'[\(\)\,\.]', ' ', desc_clean)
                desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()
                
                if desc_clean in messy_name and len(desc_clean) > 3:
                    best_match_row = row
                    exact_name = desc_clean
                    break
                    
            if best_match_row is None:
                match = self.df_ksei[self.df_ksei['Code'].astype(str).str.strip().str.upper() == exact_name.upper()]
                if match.empty:
                    match = self.df_ksei[self.df_ksei['Code'].astype(str).str.contains(exact_name, case=False, na=False, regex=False)]
                if match.empty:
                    match = self.df_ksei[self.df_ksei['Description'].astype(str).str.contains(exact_name, case=False, na=False, regex=False)]
                    
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