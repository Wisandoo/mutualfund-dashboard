# Deployment Guide

Panduan ini menjelaskan prosedur untuk men-deploy sistem *Mutual Fund Dashboard* ke lingkungan produksi (Production). Sistem ini terdiri dari dua komponen utama: **Backend (Django)** dan **Frontend (Next.js)**.

## 1. Persiapan Produksi (Backend)

### Lingkungan Server
*   **Web Server:** Nginx (sebagai *reverse proxy*).
*   **WSGI Server:** Gunicorn.
*   **Database:** PostgreSQL atau MySQL.

### Konfigurasi Backend
1.  **Environment Variables:** Pastikan file `.env` di server produksi dikonfigurasi dengan benar:
    ```env
    DEBUG=False
    SECRET_KEY=your_secure_random_string
    ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
    DATABASE_URL=...
    ```
2.  **Dependencies:** Instal dependensi produksi:
    ```bash
    pip install -r requirements.txt
    pip install gunicorn
    ```
3.  **Static Files:** Jalankan perintah berikut untuk mengumpulkan file statis:
    ```bash
    python manage.py collectstatic --noinput
    ```
4.  **Process Manager:** Gunakan Gunicorn untuk menjalankan aplikasi. Contoh perintah (bisa diintegrasikan dengan Systemd/Supervisor):
    ```bash
    gunicorn --workers 3 --bind unix:/run/gunicorn.sock config.wsgi:application
    ```

## 2. Persiapan Produksi (Frontend)

### Build Frontend
1.  **Environment Variables:** Pastikan file `.env.production` terisi:
    ```env
    NEXT_PUBLIC_API_URL=[https://api.yourdomain.com/api](https://api.yourdomain.com/api)
    ```
2.  **Build Process:**
    ```bash
    npm install
    npm run build
    ```

### Deployment (Vercel)
Cara termudah untuk mendeploy aplikasi Next.js adalah melalui Vercel:
1.  Hubungkan repositori GitHub Anda ke Vercel.
2.  Pilih `Root Directory` ke folder `frontend`.
3.  Vercel akan otomatis mendeteksi pengaturan build.
4.  Tambahkan Environment Variable `NEXT_PUBLIC_API_URL` pada panel *Settings > Environment Variables* di dashboard Vercel.
5.  Klik **Deploy**.

## 3. Konfigurasi Nginx (Reverse Proxy)

Jika Anda menggunakan VPS (seperti Ubuntu), konfigurasikan Nginx untuk melayani *backend*:

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location /static/ {
        alias /path/to/your/backend/static/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}