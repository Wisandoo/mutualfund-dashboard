class SectionService:
    @staticmethod
    def get_section(text, start_keyword, end_keyword=None):
        """Mendapatkan teks tepat di antara dua kata kunci, tidak melebar kemana-mana."""
        if not text or not start_keyword:
            return ""
        
        text_lower = text.lower()
        start_idx = text_lower.find(start_keyword.lower())
        
        if start_idx == -1:
            return ""
            
        content_start = start_idx + len(start_keyword)
        
        if end_keyword:
            end_idx = text_lower.find(end_keyword.lower(), content_start)
            if end_idx != -1:
                return text[content_start:end_idx].strip()
                
        return text[content_start:].strip()