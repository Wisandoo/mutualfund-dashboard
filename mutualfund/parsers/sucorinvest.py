import re
from mutualfund.parsers.base import BaseParser
from mutualfund.utils import get_month_en, clean_number
from mutualfund.services.section_service import SectionService

class SucorinvestParser(BaseParser):

    def parse(self, text):
        ffs_data = self.get_template()
        self.extract_product(text, ffs_data)
        self.extract_date(text, ffs_data)
        self.extract_aum(text, ffs_data)
        self.extract_type(text, ffs_data)
        self.extract_objective(text, ffs_data)
        self.extract_allocations(text, ffs_data)
        self.extract_top_holdings(text, ffs_data)
        
        return ffs_data

    def extract_product(self, text, ffs_data):
        sec = SectionService.get_section(text, "Profil Reksa Dana", "Tujuan Investasi")
        if not sec:
            sec = SectionService.get_section(text, "INFORMASI RINGKAS", "FITUR")
            
        m = re.search(r'(SUCORINVEST[A-Za-z0-9\s\-]+?)(?:\s+adalah|\s+\d{1,2}\s+[A-Za-z]|\n)', sec, re.IGNORECASE)
        if m: 
            ffs_data['productName'] = m.group(1).replace('\n', ' ').strip()
        else:
            m2 = re.search(r'(SUCORINVEST[A-Za-z0-9\s\-]+)', sec, re.IGNORECASE)
            if m2: ffs_data['productName'] = m2.group(1).replace('\n', ' ').strip()

    def extract_date(self, text, ffs_data):
        sec = text[:1000]
        match = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s*[-]*\s*(\d{4})', sec)
        
        if match:
            day, month, year = match.groups()
            if month.lower() == 'mel': month = 'mei'
            
            ffs_data['ffsPeriod'] = f"{get_month_en(month)}_{year}"
            m_dict = {"JAN":"01", "FEB":"02", "MAR":"03", "APR":"04", "MAY":"05", "JUN":"06", "JUL":"07", "AUG":"08", "SEP":"09", "OCT":"10", "NOV":"11", "DEC":"12"}
            ffs_data['ffsDate'] = f"{year}-{m_dict.get(get_month_en(month), '01')}-{day.zfill(2)}"

    def extract_aum(self, text, ffs_data):
        sec = SectionService.get_section(text, "Total Nilai Aktiva Bersih", "Minimum Investasi")
        if not sec: 
            sec = SectionService.get_section(text, "Aktiva Bersih", "\n")
            
        m = re.search(r'(Rp|IDR|USD|\$)\s*([\d\.,]+)\s*(Milyar|Miliar|Triliun|Juta|M|T)', sec, re.IGNORECASE)
        if m:
            curr = m.group(1).upper()
            is_usd = 'USD' in curr or '$' in curr or 'dollar amerika' in text.lower()
            ffs_data['currency'] = 'USD' if is_usd else 'IDR'
            
            mult_str = m.group(3).lower()
            multiplier = 1e6
            if 'triliun' in mult_str or 't' == mult_str: multiplier = 1e12
            elif 'milyar' in mult_str or 'miliar' in mult_str: multiplier = 1e9
            
            ffs_data['aum'] = clean_number(m.group(2)) * multiplier
            ffs_data['totalAum'] = int(ffs_data['aum'])

    def extract_type(self, text, ffs_data):
        sec = SectionService.get_section(text, "Jenis Reksa Dana", "\n")
        if not sec:
            sec = SectionService.get_section(text, "Profil Reksa Dana", "Tujuan")
            
        j_type = sec.upper()
        if "SAHAM" in j_type or "EKUITAS" in j_type: ffs_data['mfType'] = "SAHAM"
        elif "UANG" in j_type: ffs_data['mfType'] = "PASAR UANG"
        elif "SUKUK" in j_type: ffs_data['mfType'] = "SUKUK"
        elif "TETAP" in j_type or "OBLIGASI" in j_type: ffs_data['mfType'] = "PENDAPATAN TETAP"
        elif "INDEKS" in j_type: ffs_data['mfType'] = "INDEKS"
        else: ffs_data['mfType'] = "CAMPURAN"

    def extract_objective(self, text, ffs_data):
        sec = SectionService.get_section(text, "Tujuan Investasi", "Jenis Reksa Dana")
        if not sec or len(sec) > 500:
            sec = SectionService.get_section(text, "Tujuan Investasi", "Kebijakan Investasi")
            
        ffs_data['investmentObjective'] = sec.replace("\n", " ").strip()

    def extract_allocations(self, text, ffs_data):
        sec = SectionService.get_section(text, "Alokasi Aset", "Komposisi Geografis")
        if not sec or len(sec) > 300:
            sec = SectionService.get_section(text, "Alokasi Aset", "Alokasi Efek Terbesar")

        garbage_patterns = [
            r'(?i)risiko\s+likuiditas[^\n]*',
            r'(?i)risiko\s+perubahan\s+peraturan[^\n]*',
            r'(?i)risiko\s+nilai\s+tukar[^\n]*',
            r'(?i)risiko\s+terkait[^\n]*',
            r'(?i)risiko\s+penyesuaian[^\n]*'
        ]
        for p in garbage_patterns:
            sec = re.sub(p, '', sec)
            
        matches = re.findall(r'([^:%]+?)\s*:\s*(-?[\d\.,]+)\s*%', sec)
        
        alloc_dict = {}
        for name_raw, pct_raw in matches:
            n = name_raw.replace('\n', ' ').strip()
            try:
                pct_str = pct_raw.replace(',', '.')
                pct = float(pct_str)
            except ValueError:
                continue

            alloc_dict[n] = alloc_dict.get(n, 0.0) + pct
                
        for k, v in alloc_dict.items():
            ffs_data['portfolioAllocations'].append({"name": k, "percentage": round(v, 2)})

    def extract_top_holdings(self, text, ffs_data):
        sec = SectionService.get_section(text, "Alokasi Efek Terbesar", "PT. SUCORINVEST ASSET")
        if not sec:
            sec = SectionService.get_section(text, "Alokasi Efek Terbesar", "Kinerja")
            
        if not sec:
            return

        sec_clean = re.sub(r'\s+', ' ', sec)
        sec_clean = sec_clean.replace('|', ' ')
        
        # --- 1. AGGRESSIVE STATIC NOISE REMOVAL ---
        # Menghapus paksa seluruh teks Alokasi Aset yang menyeberang dari kolom kiri
        noises = [
            r"Komposisi Geografis", r"Dalam Negeri\s*:\s*[\d\.,]+%", r"Luar Negeri\s*:\s*[\d\.,]+%",
            r"Alokasi Aset", r"Alokasi Efek Terbesar", r"Berdasarkan Urutan Abjad",
            r"Nama Efek", r"Jenis Efek", r"%\s*Kepemilikan",
            r"Efek Ekuitas Syariah", r"Efek Ekuitas",
            r"Inst\.?\s*Psr\.?\s*Uang.*?Setara Kas",
            r"Inst\.?\s*Psr\.?\s*Uang.*?Deposito Syariah",
            r"&/\s*Deposito Syariah",
            r"SBSN\s*&/\s*Sukuk Korporasi",
            r"Obligasi\s*&/\s*Sukuk Pemerintah RI\s*&?\s*BUMN Infrastruktur",
            r"Obligasi\s*&/\s*Sukuk Korporasi",
            r"Efek Syariah Berpendapatan Tetap",
            r"Sukuk\s*\(dgn.*?\)",
            r"Sukuk\s*&/\s*SBSN",
            r"Efek Hutang"
        ]
        
        for noise in noises:
            sec_clean = re.sub(noise, ' ', sec_clean, flags=re.IGNORECASE)

        # Hapus Dynamic Allocation
        for alloc in ffs_data.get('portfolioAllocations', []):
            alloc_pat = r'\s+'.join([re.escape(word) for word in alloc['name'].split()])
            sec_clean = re.sub(alloc_pat, ' ', sec_clean, flags=re.IGNORECASE)

        # --- 2. REGEX MATCHING ---
        pat = r'([A-Za-z0-9\.\,\-\&\s\(\)\/]+?)\s+(Obligasi|Saham|Pasar\s*Uang|Equity|Cash|EBU|Sukuk|Deposito)\s*([\d\.,]+)\s*(?:%)?'
        matches = re.findall(pat, sec_clean, re.IGNORECASE)
        
        count = 0
        for name_raw, t_type, pct_raw in matches:
            if count >= 10: break
            
            n = name_raw.strip()
            n = re.sub(r'^[\d\.\,\%]+\s*|[:]+', '', n).strip()
            
            pct = clean_number(pct_raw)
            if len(n) > 3 and 0 < pct <= 100:
                enriched = self.ksei_service.enrich_holding_data(n, ffs_data.get('ffsDate', ''))
                enriched['percentage'] = pct
                ffs_data['topHoldings'].append(enriched)
                count += 1