import re

def get_month_en(indonesian_month):
    months = {
        "januari": "JAN", "februari": "FEB", "maret": "MAR", "april": "APR", 
        "mei": "MAY", "juni": "JUN", "juli": "JUL", "agustus": "AUG", 
        "september": "SEP", "oktober": "OCT", "november": "NOV", "desember": "DEC"
    }
    return months.get(indonesian_month.lower(), "JAN")

def clean_number(text_num):
    s = re.sub(r'[^\d\.,]', '', text_num)
    if len(s) % 2 == 0 and len(s) > 0:
        if all(s[i] == s[i+1] for i in range(0, len(s), 2)):
            s = s[::2]
    s = s.replace(',', '.')
    s = re.sub(r'\.+', '.', s)
    try: 
        return float(s)
    except ValueError: 
        return 0.0
    
def normalize_pdf_text(text):
    if not text: 
        return ""
    
    # 1. Bersihkan non-breaking space
    text = text.replace("\xa0", " ")
    
    lines = text.split('\n')
    res_lines = []
    
    for line in lines:
        if not line.strip():
            res_lines.append(line)
            continue
            
        # Tokenisasi dengan mempertahankan spasi asli
        tokens = re.split(r'([ \t]+)', line)
        
        doubled_count = 0
        normal_count = 0
        
        # Hitung jumlah token yang kemungkinan merupakan shadow text (karakter ganda sempurna)
        for t in tokens:
            if not t.strip(): 
                continue
            if len(t) >= 4 and len(t) % 2 == 0 and t[0::2] == t[1::2]:
                doubled_count += 1
            elif len(t) >= 3:
                normal_count += 1
                
        is_shadow_line = doubled_count > 0 and doubled_count >= normal_count
        
        res_tokens = []
        for t in tokens:
            if not t.strip():
                res_tokens.append(t)
                continue
                
            # Proses deduplikasi karakter berbayang (misal: "PPrrooffiill" -> "Profil")
            if is_shadow_line:
                if len(t) % 2 == 0 and t[0::2] == t[1::2]:
                    res_tokens.append(t[0::2])
                else:
                    res_tokens.append(t)
            else:
                # Deduplikasi konservatif hanya untuk kata yang sangat jelas berbayang
                if len(t) >= 4 and len(t) % 2 == 0 and t[0::2] == t[1::2]:
                    res_tokens.append(t[0::2])
                else:
                    res_tokens.append(t)
                    
        res_lines.append("".join(res_tokens))
        
    # 2. Normalisasi spasi berlebih secara horizontal, TETAP mempertahankan Line Break (\n)
    normalized_text = "\n".join(res_lines)
    normalized_text = re.sub(r'[ \t]+', ' ', normalized_text)
    
    return normalized_text

def parse_aum(aum_str):
    s = str(aum_str)

    # hapus currency
    s = re.sub(r'(?i)(rp|idr|usd|\$)', '', s).strip()

    # Format US
    # 203,557,160,557.76
    if ',' in s and '.' in s and s.rfind('.') > s.rfind(','):
        s = s.replace(',', '')

    # Format Indonesia
    # 203.557.160.557,76
    elif '.' in s and ',' in s and s.rfind(',') > s.rfind('.'):
        s = s.replace('.', '').replace(',', '.')

    elif ',' in s:
        s = s.replace(',', '.')

    multiplier = 1

    lower = s.lower()

    if re.search(r'(triliun|bio)', lower):
        multiplier = 1e12
    elif re.search(r'(miliar|milyar|bil)', lower):
        multiplier = 1e9
    elif re.search(r'(juta|jt|million)', lower):
        multiplier = 1e6

    s = re.sub(r'[^\d\.]', '', s)

    try:
        return float(s) * multiplier
    except:
        return 0.0