class BaseParser:
    def __init__(self, ksei_service):
        self.ksei_service = ksei_service

    def get_template(self):
        return {
            "ffsDate": "", "launchDate": "", "aum": 0.0, "totalAum": 0, "currency": "IDR",
            "topHoldings": [], "portfolioAllocations": [],
            "investmentObjective": "", "mfType": "", "productCode": "", 
            "productName": "", "ffsPeriod": ""
        }

    def parse(self, text):
        raise NotImplementedError("Setiap Parser spesifik harus mengimplementasikan method parse()")