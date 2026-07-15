import re
from mutualfund.parsers.base import BaseParser
from mutualfund.utils import get_month_en, clean_number, parse_aum
import itertools

class UOBSectionService:
    @staticmethod
    def get_aum_section(text):
        start = text.find("Mata Uang")
        if start == -1: start = text.find("Total Nilai Aktiva")
        if start == -1: start = text.find("Total AUM")
        end = text.find("Minimum Investasi")
        if end == -1: end = text.find("Jumlah Unit")
        if start != -1 and end != -1 and start < end:
            return text[start:end].strip()
        return text[:1500]

    @staticmethod
    def get_allocation_section(text):
        start = text.find("Komposisi Portfolio")
        if start == -1: start = text.find("Komposisi Geografis")
        if start == -1: start = text.find("Faktor Risiko Utama")
        end = text.find("Kinerja Reksa Dana")
        if end == -1: end = text.find("Kinerja Bulan")
        if end == -1: end = text.find("Kinerja")
        if start != -1 and end != -1 and start < end:
            return text[start:end].strip()
        return text

    @staticmethod
    def get_holding_section(text):
        start = text.find("Nama Efek")
        if start == -1: start = text.find("Portofolio 10 Terbesar")
        end = text.find("* disusun berdasarkan")
        if end == -1: end = text.find("Klasifikasi Risiko")
        if end == -1: end = text.find("Kinerja Reksa Dana")
        if start != -1 and end != -1 and start < end:
            return text[start:end].strip()
        return text


class UOBParser(BaseParser):

    def parse(self, text, pdf_path=None):
        ffs_data = self.get_template()
        text_clean = text.replace("\xa0", " ")
        
        self.extract_product(text_clean, ffs_data)
        self.extract_date(text_clean, ffs_data)
        self.extract_aum(text_clean, ffs_data)
        self.extract_fund_type(text_clean, ffs_data)
        self.extract_objective(text_clean, ffs_data)
        self.extract_allocations(text_clean, ffs_data)
        self.extract_top_holdings(text_clean, ffs_data)
        
        return ffs_data

    def extract_product(self, text, ffs_data):
        sec = text[:700] 
        match = re.search(r'(UOBAM\s+[A-Za-z0-9\s\-]+?)(?=\s+\d{1,2}\s+[A-Za-z]+\s+\d{4})', sec, re.IGNORECASE)
        if match: ffs_data["productName"] = " ".join(match.group(1).split())

    def extract_date(self, text, ffs_data):
        sec = text[:1000]
        match = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', sec)
        if match:
            day, month, year = match.groups()
            ffs_data['ffsPeriod'] = f"{get_month_en(month)}_{year}"
            m_dict = {"JAN":"01", "FEB":"02", "MAR":"03", "APR":"04", "MAY":"05", "JUN":"06", "JUL":"07", "AUG":"08", "SEP":"09", "OCT":"10", "NOV":"11", "DEC":"12"}
            ffs_data['ffsDate'] = f"{year}-{m_dict.get(get_month_en(month), '01')}-{day.zfill(2)}"

    def extract_aum(self, text, ffs_data):
        sec = UOBSectionService.get_aum_section(text)
        match = re.search(r'(?:Total AUM|Nilai Aktiva Bersih).*?(Rp|IDR|USD|\$)\s*([\d\.,\s]+)', sec, re.IGNORECASE | re.DOTALL)
        if match:
            curr = match.group(1).upper()
            ffs_data['currency'] = 'USD' if 'USD' in curr or '$' in curr else 'IDR'
            raw_aum = match.group(2).strip()
            
            multiplier = 1
            m_mult = re.search(r'(Milyar|Miliar|Triliun|Juta|M|T)\b', sec, re.IGNORECASE)
            if m_mult:
                mult_str = m_mult.group(1).lower()
                if 'triliun' in mult_str or 't' == mult_str: multiplier = 1e12
                elif 'milyar' in mult_str or 'miliar' in mult_str: multiplier = 1e9
                elif 'juta' in mult_str or 'm' == mult_str: multiplier = 1e6
                
            ffs_data["aum"] = parse_aum(raw_aum)
            ffs_data["totalAum"] = int(ffs_data["aum"])

    def extract_fund_type(self, text, ffs_data):
        sec = text[:1000]
        match = re.search(r'Reksa\s*Dana\s*(Indeks|Campuran|Saham|Pasar Uang|Pendapatan Tetap|Ekuitas)', sec, re.IGNORECASE)
        if match:
            j_type = match.group(1).upper()
            if "SAHAM" in j_type or "EKUITAS" in j_type: ffs_data['mfType'] = "SAHAM"
            elif "UANG" in j_type: ffs_data['mfType'] = "PASAR UANG"
            elif "TETAP" in j_type: ffs_data['mfType'] = "PENDAPATAN TETAP"
            elif "INDEKS" in j_type: ffs_data['mfType'] = "INDEKS"
            else: ffs_data['mfType'] = "CAMPURAN"
        else:
            ffs_data['mfType'] = "CAMPURAN"

    def extract_objective(self, text, ffs_data):
        start = text.find("Tujuan Investasi")
        end = text.find("Deskripsi Produk")
        if end == -1: end = text.find("Kebijakan Investasi")
        if start != -1 and end != -1 and start < end:
            sec = text[start+len("Tujuan Investasi"):end]
            ffs_data['investmentObjective'] = sec.replace("\n", " ").strip()

    def extract_allocations(self, text, ffs_data):
        sec = UOBSectionService.get_allocation_section(text)
        all_percentages = []
        for p in re.findall(r'([\d\.,]+)\s*%', sec):
            val = clean_number(p)
            if 0 < val <= 100: all_percentages.append(val)
                
        valid_percentages = []
        for r in range(1, min(6, len(all_percentages) + 1)):
            for combo in itertools.combinations(all_percentages, r):
                if 99.9 <= sum(combo) <= 100.1:
                    valid_percentages = sorted(list(combo), reverse=True)
                    break
            if valid_percentages: break
        if not valid_percentages: valid_percentages = sorted(all_percentages, reverse=True)
            
        categories = []
        for line in sec.split('\n'):
            line = line.strip()
            clean_line = re.sub(r'\s+(Equity|Cash|Bonds|Deposits|Saham|Obligasi|Pasar\s*Uang)\s+[\d\.,]+\s*%?\s*$', '', line)
            found_cats = re.findall(r'\b(Equity|Cash|Bonds|Deposits|Saham|Obligasi|Pasar\s*Uang)\b', clean_line)
            for cat in found_cats:
                c = cat.title()
                if c not in categories: categories.append(c)
                    
        limit = min(len(valid_percentages), len(categories))
        for i in range(limit):
            ffs_data['portfolioAllocations'].append({"name": categories[i], "percentage": valid_percentages[i]})
            
    def extract_top_holdings(self, text, ffs_data, pdf_path=None):
        sec = UOBSectionService.get_holding_section(text)
        count = 0
        
        pat = re.compile(r'([A-Za-z0-9\.\,\-\&\/\(\)\s]+?)\s+(Equity|Cash|Bonds|Deposits|Saham|Obligasi|Pasar\s*Uang)\s+([\d\.,]+)\s*%?$', re.IGNORECASE | re.MULTILINE)

        noises_to_remove = [
            r"-\s*Risiko.*?",
            r"Kondisi Ekonomi dan Politik",
            r"Ekonomi dan Politik",
            r"berkurangnya NAB setiap UP",
            r"perubahan portofolio efek dengan indeks acuan",
            r"perubahan portofolio",
            r"penyesuaian portofolio efek dengan indeks acuan",
            r"penyesuaian portofolio",
            r"wanprestasi",
            r"likuiditas",
            r"peraturan",
            r"nilai tukar",
            r"suku bunga",
            r"Detail mengenai risiko dan risiko lainnya dapat dilihat pada",
            r"Prospektus\.",
            r"Klasifikasi Risiko",
            r"Rendah Sedang Tinggi",
            r"Cash", r"Bonds", r"Deposits", r"Saham", r"Equity", r"Pasar Uang"
        ]
        
        for line in sec.split('\n'):
            if count >= 10: break
            
            match = pat.search(line.strip())
            if match:
                raw_name = match.group(1).strip()

                if '%' in raw_name: 
                    raw_name = raw_name.split('%')[-1].strip()

                clean_name = raw_name
                for _ in range(3):
                    for noise in noises_to_remove:
                        clean_name = re.sub(rf'^{noise}\s+', '', clean_name, flags=re.IGNORECASE).strip()
                
                pct = clean_number(match.group(3))
                if len(clean_name) > 3 and 0 < pct <= 100:
                    enriched = self.ksei_service.enrich_holding_data(clean_name, ffs_data.get('ffsDate', ''))
                    enriched['percentage'] = pct
                    ffs_data['topHoldings'].append(enriched)
                    count += 1