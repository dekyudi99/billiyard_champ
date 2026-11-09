# Billiard Championship - World Esports Management System

Sistem manajemen dan pelacakan turnamen Billiard Championship berbasis Web modern dan otomatis, dibangun untuk menggantikan pencatatan manual berbasis Microsoft Excel (36 file spreadsheet) secara terintegrasi dan real-time.

---

## 🌟 Fitur Utama

1. **Pengganti Otomatis Seluruh File Excel**:
   - **28 File MPL Regional**: Mengelola 7 wilayah (AM, ID, MEA, MY, PEL, PH, SEA) dari Season 1 s/d Season 4.
   - **3 File MSL Championship**: Kejuaraan internasional sekunder (Season 1 s/d 3).
   - **3 File M Championship**: Kejuaraan dunia tertinggi M-Series (M1, M2, M3).
   - **ROAD TO WORLD CHAMPION.xlsx**: Bagan otomatis menuju M4 (16 Tim) dan MSL S4 (8 Tim).
   - **BEST TEAM OF ALL TIME.xlsx**: Klasemen akumulatif otomatis *Base Team* (42 Tim) dan *Base Region* (7 Wilayah).

2. **Perhitungan Poin Real-Time (Base Team & Base Region)**:
   - Ketika skor pertandingan atau hasil turnamen disimpan, sistem secara otomatis menghitung ulang seluruh poin tim, peringkat dunia, serta perolehan medali/trofi emas, perak, dan perunggu.
   - Poin regional (*International Point Coefficient*) diperbarui secara otomatis berdasarkan kontribusi tim-timnya di M-Championship dan MSL.

3. **Logika Kualifikasi Slot M-Championship & MSL S4**:
   - **M-Championship (16 Slot)**:
     - 14 Slot Reguler: Juara 1 (#1) dan Runner-up (#2) dari ke-7 region MPL.
     - Slot 15: **Peringkat 3 dari Region Juara Bertahan M-Championship sebelumnya**. Contoh: Juara M3 adalah T1 dari PEL, maka peringkat 3 PEL S4 (**DRX**) langsung lolos ke M4.
     - Slot 16: **Juara 1 MSL Championship** (`MSL #1`).
   - **MSL Championship (8 Slot)**:
     - 6 Region Reguler mengirim Peringkat 3 MPL masing-masing (C9, ONIC, FLCN, HBSE, FLCP, SEA #3).
     - Region Juara Bertahan M-Championship (PEL) yang peringkat 3-nya sudah promosi ke M4, mengirim **Peringkat 4** (**IHC**)!
     - **Slot ke-8 (Slot Ekstra MSL)**: Dapat disesuaikan melalui menu pengaturan:
       - **Opsi 1 (Sesuai File Excel Asli)**: Diberikan kepada peringkat 5 dari Region Juara Bertahan M-Series (**Dplus KIA / DK** dari PEL).
       - **Opsi 2 (Region Juara Bertahan MSL)**: Diberikan kepada peringkat 4 dari region juara MSL sebelumnya (**G2** dari MEA).
       - **Opsi 3 (Custom Wildcard)**: Bebas ditentukan oleh admin/pengguna.

4. **Simulator Interaktif MPL SEA S4**:
   - Tombol 1-klik untuk mensimulasikan hasil MPL SEA S4 (yang belum bertanding di file asli) untuk mendemonstrasikan bagaimana slot kosong `SEA #1`, `SEA #2`, dan `SEA #3` terisi seketika dan klasemen langsung ter-update.

---

## 🚀 Menjalankan dengan Docker (Rekomendasi)

Sistem telah dilengkapi dengan `Dockerfile` dan `docker-compose.yml`. Cukup jalankan satu perintah:

```bash
docker compose up --build
```

Setelah container berjalan, buka browser di:
👉 **`http://localhost:8000`**

Untuk menghentikan container:
```bash
docker compose down
```

---

## 💻 Menjalankan Secara Lokal (Tanpa Docker)

Jika ingin menjalankan langsung menggunakan Python:

1. Masuk ke direktori backend:
```bash
cd web-app/backend
```

2. Install dependency:
```bash
pip install -r requirements.txt
```

3. Jalankan server:
```bash
uvicorn main:app --reload --port 8000
```

4. Buka di browser:
👉 **`http://localhost:8000`**

---

## 🗄️ Struktur Proyek

```
web-app/
├── backend/
│   ├── main.py              # FastAPI Web Server & REST API
│   ├── database.py          # SQLite Schema & Koneksi
│   ├── rules_engine.py      # Logika Kualifikasi Slot & Rekalkulasi Poin
│   ├── seed_data.py         # Seeding Data Awal dari Seluruh File Excel
│   ├── requirements.txt     # Daftar Paket Python
│   └── billiard_championship.db
├── frontend/
│   ├── index.html           # Single Page Application (Tailwind CSS + Vue 3)
│   ├── app.js               # Reactive State & API Handlers
│   └── style.css            # Custom Styling & Animations
├── logos/                   # 43 Logo Tim Esport Lengkap
├── Dockerfile               # Konfigurasi Container Docker
├── docker-compose.yml       # Konfigurasi Docker Compose
└── README.md
```

