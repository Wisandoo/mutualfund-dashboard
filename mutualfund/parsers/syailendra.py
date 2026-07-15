import re
from mutualfund.parsers.base import BaseParser
from mutualfund.utils import parse_aum, clean_number

class SyailendraParser(BaseParser):

    def parse(self, text, pdf_path=None):
        ffs_data = self.get_template()

        # 1. PARSING NAMA PRODUK
        prod_match = re.search(r'REKSA DANA\s+([A-Za-z0-9\s\-]+)', text, re.IGNORECASE)
        if prod_match:
            clean_name = prod_match.group(1).split('\n')[0].strip()
            ffs_data['productName'] = clean_name
        
        # 2. PARSING AUM
        aum_match = re.search(r'Total Nilai Aktiva Bersih\s*Rp\s*([\d\.,]+\s*(?:triliun|miliar|milyar))', text, re.IGNORECASE)
        if aum_match: 
            ffs_data['aum'] = parse_aum(aum_match.group(1))
            ffs_data['totalAum'] = int(ffs_data['aum'])

        # 3. PARSING TANGGAL
        date_match = re.search(r'(\d{2})/([A-Za-z]+)/(\d{4})', text)
        if date_match:
            day, month, year = date_match.groups()
            ffs_data['ffsPeriod'] = f"{month.upper()}_{year}"
            ffs_data['ffsDate'] = f"{year}-05-29"
        
        # 4. PARSING TIPE REKSA DANA
        text_intro = text[:500]
        if "Pasar Uang" in text_intro: ffs_data['mfType'] = "PASAR UANG"
        elif "Ekuitas" in text_intro: ffs_data['mfType'] = "EKUITAS"
        elif "Pendapatan Tetap" in text_intro: ffs_data['mfType'] = "PENDAPATAN TETAP"
        elif "Indeks" in text_intro: ffs_data['mfType'] = "INDEKS"
        else: ffs_data['mfType'] = "CAMPURAN"

        # 5. PARSING ALOKASI ASET
        if "Alokasi Aset" in text:
            alloc_chunk = text.split("Alokasi Aset", 1)[-1]
            
            if "Keterangan Resiko" in alloc_chunk:
                alloc_chunk = alloc_chunk.split("Keterangan Resiko")[0]
            elif "Kinerja Bulan" in alloc_chunk:
                alloc_chunk = alloc_chunk.split("Kinerja Bulan")[0]
                
            alloc_matches = re.findall(r'(Saham|Obligasi|Deposito|Kas\&Setara|Kas)\s*([\d\.,]+)%', alloc_chunk, re.IGNORECASE)
            
            alloc_dict = {}
            for cat, pct_str in alloc_matches:
                cat_lower = cat.lower()
                if "saham" in cat_lower: norm_cat = "Saham"
                elif "obligasi" in cat_lower: norm_cat = "Obligasi"
                elif "deposito" in cat_lower: norm_cat = "Deposito"
                elif "kas&setara" in cat_lower: norm_cat = "Kas & Setara"
                elif "kas" in cat_lower: norm_cat = "Kas"
                else: norm_cat = cat.strip().title()
                    
                pct = float(pct_str.replace(',', '.'))
                alloc_dict[norm_cat] = alloc_dict.get(norm_cat, 0.0) + pct
                
            for k, v in alloc_dict.items():
                ffs_data['portfolioAllocations'].append({"name": k, "percentage": round(v, 2)})

        # 6. PARSING TOP 10 HOLDINGS
        holdings_match = re.findall(r'\d+\.\s+([A-Za-z0-9\.\-\/\&]+(?:\s+[A-Za-z0-9\.\-\/\&]+)*)\s+([\d\.,]+)%', text)
        
        count = 0
        for code, pct in holdings_match:
            if count >= 10: break
            
            code_clean = code.strip()
            pct_float = clean_number(pct)
            
            if len(code_clean) > 3 and 0 < pct_float <= 100:
                enriched = self.ksei_service.enrich_holding_data(code_clean, ffs_data.get('ffsDate', ''))
                enriched['percentage'] = pct_float
                ffs_data['topHoldings'].append(enriched)
                count += 1

        return ffs_data