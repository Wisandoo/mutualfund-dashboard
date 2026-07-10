import os
import json

class SQLService:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.queries = {"UOB": [], "Sucorinvest": [], "Syailendra": []}
        os.makedirs(self.output_dir, exist_ok=True)

    def add_query(self, mi_name, ffs_data):
        valid_sql_date = ffs_data['ffsDate'] if len(ffs_data['ffsDate']) == 10 else "2026-06-30" 
        json_data_str = json.dumps(ffs_data, ensure_ascii=False).replace("'", "''")
        
        sql = f"""INSERT INTO mutualfund_ffs (product_code, ffs_date, data, aum, created_datetime) 
                  VALUES ('{ffs_data['productCode']}', '{valid_sql_date}', '{json_data_str}', '{ffs_data['totalAum']}', now()) 
                  ON DUPLICATE KEY UPDATE data = VALUES(data), aum = VALUES(aum), latest = 1, created_datetime = now();"""
        
        if mi_name in self.queries:
            self.queries[mi_name].append(sql)

    def save_all(self, stdout_func):
        for mi, queries in self.queries.items():
            if queries:
                filepath = os.path.join(self.output_dir, f"{mi}_insert.sql")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("\n\n".join(queries))
                stdout_func(f"Berhasil membuat SQL untuk {mi}")