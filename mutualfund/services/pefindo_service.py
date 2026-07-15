import pdfplumber
import pandas as pd
import re

class PefindoService:
    def __init__(self, pdf_path):
        self.df_pefindo = pd.DataFrame()
        if pdf_path:
            self._parse_pdf(pdf_path)

    def _parse_pdf(self, pdf_path):
        data = []
        current_issuer = "Unknown"

        headers_to_skip = [
            "PEFINDO", "Credit Rating", "Sektor Industri", "Nilai Emisi", 
            "Jatuh Tempo", "Sebelumnya", "Peringkat", "Saat Ini", "Berakhir",
            "Outlook", "Status", "(Rp miliar)"
        ]

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    words = page.extract_words()
                    if not words: continue
                    
                    # 1. Kuantisasi Y-Axis (Pembulatan spasial vertikal per 4 piksel)
                    lines_dict = {}
                    for w in words:
                        y_key = round(w['top'] / 4) * 4
                        if y_key not in lines_dict:
                            lines_dict[y_key] = []
                        lines_dict[y_key].append(w)
                    
                    # 2. X-Axis Sorting & Rekonstruksi Baris Horizontal
                    sorted_y = sorted(lines_dict.keys())
                    for y in sorted_y:
                        sorted_words = sorted(lines_dict[y], key=lambda x: x['x0'])
                        line = " ".join([w['text'] for w in sorted_words])
                        
                        # 3. FSM Sederhana (Halt condition untuk area Footer PDF)
                        if "DISCLAIMER" in line.upper() or "RATINGS SUFFIX" in line.upper():
                            self.df_pefindo = pd.DataFrame(data)
                            return # Hentikan parser sepenuhnya karena sudah mencapai akhir
                            
                        # Abaikan baris yang memuat header
                        if any(h.upper() in line.upper() for h in headers_to_skip):
                            continue
                            
                        # Deteksi Record Obligasi
                        is_bond = any(kw in line.upper() for kw in ["OBLIGASI", "SUKUK", "MTN", "SURAT", "EBA", "KIK", "LTN"])
                        
                        if is_bond:
                            # Ekstrak Tanggal Jatuh Tempo (Contoh: 9-Sep-27)
                            dates = re.findall(r'\d{1,2}-[A-Za-z]{3,4}-\d{2}', line)
                            maturity_date = dates[0] if dates else None
                            
                            if not maturity_date:
                                continue
                            
                            # Pisahkan nama obligasi dari nilai emisi
                            raw_part = line.split(maturity_date)[0].strip()
                            bond_name = re.sub(r'\s+[\d\.,]+$', '', raw_part).strip()
                            
                            # Ekstrak Frekuensi Kupon
                            freqs = re.findall(r'\b(Q|SA|A|M|0)\b', line)
                            coupon = freqs[0] if freqs else "N/A"
                            
                            # Ekstrak Rating PEFINDO
                            ratings = re.findall(r'\b(idAAA|idAA|idA|idBBB|idBB|idB|idC|idD|idSD|AAA|AA|A|BBB|BB|B|C|D|SD)(?:\([\w]+\))*(?:[\+\-])?\b', line)
                            rating = ratings[-1] if ratings else "Unknown"
                            
                            data.append({
                                "issuer": current_issuer,
                                "bond_name": bond_name,
                                "maturity_date": maturity_date,
                                "coupon_frequency": coupon,
                                "rating": rating
                            })
                        else:
                            # Jika bukan obligasi dan bukan angka jatuh tempo, pastikan ini adalah baris Emiten
                            if len(line) > 3 and not re.search(r'\d{1,2}-[A-Za-z]{3,4}-\d{2}', line):
                                clean_issuer = line.replace('Peringkat perusahaan', '').strip()
                                # Proteksi tambahan agar tidak menangkap N.A. sebagai emiten
                                if clean_issuer and "N.A." not in clean_issuer:
                                    current_issuer = clean_issuer
                                    
            self.df_pefindo = pd.DataFrame(data)
        except Exception as e:
            print(f"Error parsing PEFINDO: {e}")

    def _clean_token(self, name_str):
        n = str(name_str).upper()
        
        # Canonicalization dasar
        n = n.replace('&', 'AND')
        
        # Buang karakter non-alfanumerik
        n = re.sub(r'[^A-Z0-9\s]', ' ', n)
        
        # Filter Stopwords Finansial (Pembuang Boilerplate)
        stopwords = {
            'PT', 'TBK', 'PERSERO', 'OBLIGASI', 'SUKUK', 'BERKELANJUTAN', 
            'TAHAP', 'TAHUN', 'SERI', 'DENGAN', 'TINGKAT', 'BUNGA', 'TETAP', 
            'BERWAWASAN', 'LINGKUNGAN', 'SOSIAL', 'ORANGE', 'SYARIAH', 
            'MUDHARABAH', 'IJARAH', 'WAKALAH', 'SUBORDINASI', 'JANGKA', 
            'MENENGAH', 'PANJANG', 'KUPON', 'TERKAIT', 'KEBERLANJUTAN'
        }
        
        tokens = n.split()
        cleaned = [t for t in tokens if t not in stopwords]
        return " ".join(cleaned)

    def find_bond(self, bond_name):
        if self.df_pefindo.empty or not bond_name:
            return None
            
        query_clean = self._clean_token(bond_name)
        q_tokens = set(query_clean.split())
        
        if not q_tokens:
            return None
        
        best_match = None
        highest_score = 0.0
        
        for _, row in self.df_pefindo.iterrows():
            pef_clean = self._clean_token(str(row['issuer']) + " " + str(row['bond_name']))
            p_tokens = set(pef_clean.split())
            
            if not p_tokens:
                continue
            
            # 1. Exact Match pada representasi yang sudah dibersihkan
            if query_clean == pef_clean:
                return row
                
            # 2. Token Similarity (Jaccard Index)
            intersection = q_tokens.intersection(p_tokens)
            union = q_tokens.union(p_tokens)
            score = len(intersection) / len(union)
            
            # Komparasi Bebas Paradoks
            if score > highest_score and score > 0.4:
                highest_score = score
                best_match = row
                
        return best_match