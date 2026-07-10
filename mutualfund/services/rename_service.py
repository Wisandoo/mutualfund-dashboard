import os
import shutil

class RenameService:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def copy_and_rename(self, filepath, product_code, ffs_period):
        if not product_code or not ffs_period:
            return False

        new_pdf_name = f"{product_code}_FS_{ffs_period}.pdf"
        new_pdf_path = os.path.join(self.output_dir, new_pdf_name)
        
        try:
            shutil.copy2(filepath, new_pdf_path)
            return True
        except PermissionError:
            print(f"Gagal copy file, permission denied.")
            return False
        except Exception:
            return False