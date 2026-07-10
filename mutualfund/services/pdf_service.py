import pdfplumber

class PDFService:
    @staticmethod
    def extract_text(filepath):
        text = ""
        try:
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        except Exception as e:
            print(f"Error membaca PDF {filepath}: {e}")
        return text