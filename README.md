# Mutual Fund Fact Sheet Dashboard

## Overview
Sebuah sistem cerdas untuk mengekstrak, menyimpan, dan memvisualisasikan data dari dokumen *Fund Fact Sheet* (FFS) Reksa Dana. Proyek ini mengotomatiskan pembacaan dokumen PDF dari berbagai Manajer Investasi (seperti Sucorinvest, Syailendra, dan UOB) dan menampilkannya dalam *dashboard* interaktif.

## Core Features
*   **Automated PDF Parsing:** Mengekstrak data krusial secara otomatis menggunakan Python Regex dan PDFPlumber (AUM, Tanggal Laporan, Alokasi Aset, Top 10 Holdings, dll).
*   **Smart Data Normalization:** Membersihkan hasil OCR yang berantakan dan mengkategorikan kelas aset secara otomatis (Saham, Efek Utang, Pasar Uang).
*   **Interactive Dashboard:** Antarmuka modern untuk memfilter produk berdasarkan Manajer Investasi, Jenis Produk, Kategori (Syariah/Konvensional), dan Mata Uang.
*   **Visualisasi Dinamis:** Menggunakan Recharts untuk menampilkan alokasi aset dalam bentuk *Radial Bar Chart* yang akurat.
*   **Database Integration:** Pembuatan *query* SQL otomatis (`INSERT ... ON DUPLICATE KEY UPDATE`) untuk memastikan data selalu *up-to-date*.

## Technology Stack

**Frontend:**
*   Next.js / React.js
*   Tailwind CSS
*   Recharts

**Backend & Data Pipeline:**
*   Django / Django REST Framework (DRF)
*   Python (pdfplumber, re, pandas)

**Database:**
*   MySQL / MariaDB

## Local Environment Setup

### Prerequisites
*   Python 3.10+
*   Node.js (v18+)
*   MySQL/MariaDB Server

### 1. Backend Setup (Django)
Navigate to the backend directory and set up the Python environment:

```bash
git clone [https://github.com/yourusername/mutualfund-dashboard.git]
cd mutualfund-dashboard

# Buat virtual environment dan aktifkan
python -m venv .venv
source .venv/Scripts/activate  # On Windows
# source .venv/bin/activate    # On Unix/macOS

# Install dependencies
pip install -r requirements.txt

# Jalankan migrasi database
python manage.py migrate

# Jalankan server
python manage.py runserver
```

### 2. Frontend Setup (Next.js)
Buka terminal baru, masuk ke direktori frontend, dan jalankan server pengembangan:

```bash

# Install dependensi node modules
npx create-next-app@latest ffs-frontend
cd ffs-frontend

# Install recharts
npm install recharts

# Masukkan file komponen dan tipe data (Manual Copy-Paste)
- Copy/pindahkan file `page.tsx` yang Anda miliki ke dalam folder `src/app/` (timpa/replace file bawaannya).
- Copy/pindahkan folder `types` (yang berisi file `ffs.ts`) ke dalam folder `src/` (sehingga menjadi `src/types/`).

# Jalankan development server
npm run dev
```
### 3. Data Extraction Pipeline (Django Management Command)
Proses ekstraksi data PDF tidak dieksekusi melalui antarmuka web untuk menghindari *timeout* dan beban server. Sebagai gantinya, sistem ini menggunakan **Custom Django Management Command** agar proses *batching* berjalan efisien dan terintegrasi penuh dengan Django ORM.

**Cara menguji coba ekstraksi data:**
Repositori ini sudah dilengkapi dengan beberapa sampel file dokumen PDF Fund Fact Sheet di dalam direktori `ffs_input/` untuk keperluan pengujian. Anda bisa langsung menjalankan *pipeline* ekstraksi ini dengan langkah berikut:

1. Buka terminal di dalam folder proyek Anda dan pastikan *virtual environment* sudah aktif.
2. Jalankan perintah eksekusi berikut:

   ```bash
   python manage.py extract_ffs
Setelah proses ekstraksi selesai dengan sukses, sistem akan otomatis menghasilkan data di dua direktori baru:

sql_output/: Berisi file query (contoh: UOB_insert.sql, Sucorinvest_insert.sql, Syailendra_insert.sql). Lakukan import atau eksekusi file .sql ini ke dalam database MySQL Anda untuk memasukkan data Fund Fact Sheet terbaru.

ffs_output/: Berisi file PDF yang telah diekstrak dan diganti namanya secara otomatis menggunakan format Kode Produk (contoh: GAMA2EQC01EQUI01_FS_MAY_2026.pdf). Pindahkan atau copy seluruh file PDF di dalam folder ini ke direktori ffs-frontend/public/ agar file tersebut dapat diakses oleh sistem frontend.


