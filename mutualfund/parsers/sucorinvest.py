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
        
        # ====================================================
        # START PRODUCT LOOKUP DIAGNOSTIC
        # ====================================================

        import difflib


        p_name_raw = ffs_data.get("productName", "")

        target_keywords = [
            "KELAS C",
            "SOVEREIGN BALANCED",
            "MONEY MARKET USD"
        ]

        if any(k in p_name_raw.upper() for k in target_keywords):

            print("\n" + "=" * 70)
            print("PRODUCT LOOKUP DIAGNOSTIC")
            print("=" * 70)

            # ----------------------------
            # RAW NAME
            # ----------------------------
            print("RAW PRODUCT NAME")
            print(repr(p_name_raw))
            print(f"Length : {len(p_name_raw)}")

            # ----------------------------
            # NORMALIZED NAME
            # ----------------------------
            normalized_name = re.sub(r"\s+", " ", p_name_raw).strip()

            print("\nNORMALIZED PRODUCT NAME")
            print(repr(normalized_name))
            print(f"Length : {len(normalized_name)}")

            # ----------------------------
            # TEST REAL LOOKUP FUNCTION
            # ----------------------------
            print("\nTesting KseiService.match_product_code() ...")

            kode_produk, excel_name = self.ksei_service.match_product_code(
                normalized_name
            )

            if kode_produk:

                print("\nMATCH FOUND")
                print(f"Kode Produk : {kode_produk}")
                print(f"Excel Name  : {excel_name}")

            else:

                print("\nMATCH NOT FOUND")

                print("\nSearching similar product names...")

                excel_names = (
                    self.ksei_service.df_kode["nama produk"]
                    .dropna()
                    .astype(str)
                    .tolist()
                )

                similarities = []

                for db_name in excel_names:

                    score = difflib.SequenceMatcher(
                        None,
                        normalized_name.upper(),
                        db_name.upper()
                    ).ratio()

                    similarities.append((db_name, score))

                similarities.sort(
                    key=lambda x: x[1],
                    reverse=True
                )

                print("\nTop 5 Similar Products")

                for i, (name, score) in enumerate(similarities[:5], 1):

                    print(f"{i}. {repr(name)}")
                    print(f"   Similarity : {score:.3f}")

            print("=" * 70 + "\n")

        # ====================================================
        # END PRODUCT LOOKUP DIAGNOSTIC
        # ====================================================
        
        
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
            
        pat = r'([A-Za-z0-9\.\,\-\&\s\(\)\/]+?)\s+(Obligasi|Saham|Pasar\s*Uang|Equity|Cash|EBU|Sukuk)\s*([\d\.,]+)\s*(?:%)?'
        matches = re.findall(pat, sec, re.IGNORECASE | re.DOTALL)
        
        count = 0
        for name_raw, t_type, pct_raw in matches:
            if count >= 10: break
            n = re.sub(r'^(?:Nama Efek|Jenis Efek|%? Kepemilikan|\(Berdasarkan Urutan Abjad\))\s*', '', name_raw.strip(), flags=re.IGNORECASE)
            n = re.sub(r'^[\d\.\,\%]+\s*|[:]+', '', n).replace('\n', ' ').strip()
            
            pct = clean_number(pct_raw)
            if len(n) > 3 and 0 < pct <= 100:
                enriched = self.ksei_service.enrich_holding_data(n, ffs_data['ffsDate'])
                enriched['percentage'] = pct
                ffs_data['topHoldings'].append(enriched)
                count += 1