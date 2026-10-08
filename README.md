# 🌿 Nexus IoT • Stasiun Pemantauan Lingkungan & Kualitas Udara (Pos Pantau KP)

Dashboard web modern, interaktif, dan mandiri (*standalone*) untuk pemantauan kualitas udara dan iklim mikro lingkungan (*Air Quality & Environmental Weather Station*) secara real-time dari sensor IoT, dilengkapi pencatatan database SQLite otomatis per hari dan ekspor laporan Excel (CSV).

---

## ✨ Fitur Utama

- **⚡ Real-Time AJAX Telemetry (Tanpa Reload Halaman)**:
  - Pembaruan kontinu otomatis setiap 5 detik menggunakan AJAX murni (`XMLHttpRequest`).
  - Dilengkapi parameter dinamis anti-cache browser dan indikator latensi request.
- **📊 Metrik Pemantauan Lengkap (Pos Pantau KP)**:
  - **PM 2.5 & PM 10** (µg/m³): Partikulat debu halus & kasar dengan batas aman WHO & ISPU.
  - **Suhu Ambien** (°C) & **Kelembapan Udara** (% RH).
  - **Tekanan Atmosfer Barometrik** (hPa).
  - **Packet Sequence ID (`seq`)** & waktu pembaruan terakhir.
- **🟢 Klasifikasi Kualitas Udara (Standar WHO / ISPU)**:
  - Status kartu evaluasi kesehatan otomatis (*Baik*, *Sedang*, *Tidak Sehat*, *Berbahaya*).
  - Panduan rekomendasi aktivitas fisik luar ruangan dan perlindungan masker.
  - Spektrum klasifikasi interaktif yang menandai status udara saat ini.
- **📈 Grafik Tren Real-Time Multi-Tab (HTML5 Canvas)**:
  - Tab 1: Tren Partikulat (PM 2.5 vs PM 10).
  - Tab 2: Tren Iklim Lingkungan (Suhu vs Kelembapan).
  - Dilengkapi garis pemandu vertikal & hover tooltip interaktif tanpa dependensi library eksternal.
- **🗄️ Database SQLite Otomatis Per Hari (`monitoring.db`)**:
  - *Background Data Collector* berjalan kontinu di latar belakang menangkap setiap paket data baru.
  - Data diarsipkan rapi per tanggal (`YYYY-MM-DD`) dan waktu (`HH:MM:SS`).
- **📋 Riwayat Harian & Statistik di Halaman Utama**:
  - Filter tanggal melalui dropdown.
  - Ringkasan harian: Nilai Rata-rata, Tertinggi (Max), dan Terendah (Min) untuk PM 2.5, PM 10, Suhu, dan Kelembapan.
  - Tabel log interaktif menampilkan seluruh rekaman data pada hari terpilih.
- **📥 Ekspor Laporan Excel / CSV 1-Klik**:
  - Download laporan rekaman harian dalam format CSV RFC-4180 ber-UTF-8 BOM siap buka langsung di Microsoft Excel.
- **🌓 Tampilan Glassmorphism Modern**:
  - Desain frosted-glass futuristik dengan dukungan tema Gelap (*Dark Mode*) dan Terang (*Light Mode*).
  - *Sticky navigation header* agar tombol kontrol tetap terlihat saat halaman digulir.

---

## 📁 Struktur Berkas

```text
monitoring-dashboard/
├── index.html            # Frontend Dashboard (HTML5, CSS3 Glassmorphism, Vanilla JS AJAX)
├── server.py             # Web Server, CORS Reverse Proxy & SQLite Background Logger
├── start_server.bat      # Script 1-klik untuk menjalankan server di Windows
├── requirements.txt      # Informasi dependensi (Zero External Dependencies)
├── .gitignore            # Mengabaikan database lokal (*.db) dan cache Python
└── README.md             # Dokumentasi proyek
```

---

## 🚀 Persyaratan Sistem

- **Python 3.8 atau versi lebih baru** (Python 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14+).
- **Zero External Dependencies**: Menggunakan pustaka bawaan standar Python (`http.server`, `sqlite3`, `urllib`, `threading`). **Tidak memerlukan `pip install` apapun.**
- Web Browser modern (Google Chrome, Microsoft Edge, Mozilla Firefox, Safari).

---

## 💻 Cara Menjalankan

### Cara 1: Menggunakan Shortcut Windows (Paling Mudah)
Cukup **klik dua kali** file:
```cmd
start_server.bat
```
Server akan menyala dan browser akan otomatis terbuka di `http://localhost:8080`.

### Cara 2: Menjalankan via Terminal / Command Prompt
1. Buka terminal atau Command Prompt pada folder proyek.
2. Jalankan perintah:
   ```bash
   python server.py
   ```
3. Buka browser dan akses alamat:
   ```text
   http://localhost:8080
   ```

---

## 📡 Dokumentasi Endpoint REST API

Server lokal ini menyediakan endpoint API berikut:

| Method | Endpoint | Deskripsi |
| :--- | :--- | :--- |
| `GET` | `/api/data` | Meneruskan data telemetri real-time dari sensor perangkat IoT (CORS-enabled). |
| `GET` | `/api/db/dates` | Mengembalikan daftar seluruh tanggal yang tersimpan di database beserta jumlah rekaman. |
| `GET` | `/api/db/history?date=YYYY-MM-DD` | Mengambil data riwayat lengkap beserta ringkasan statistik (rata-rata, min, max) untuk tanggal tertentu. |
| `GET` | `/api/db/export-csv?date=YYYY-MM-DD` | Mengunduh file laporan harian berformat `.csv` (Excel-ready). |

---

## 🌐 Akses Multi-Device (Jaringan Lokal / Wi-Fi)

Server dikonfigurasi untuk mendengarkan seluruh antarmuka jaringan (`0.0.0.0:8080`). Perangkat lain di jaringan Wi-Fi yang sama (smartphone, tablet, laptop lain) dapat mengakses dashboard menggunakan alamat IP lokal laptop/komputer host:

```text
http://<IP_KOMPUTER_HOST>:8080
```
*(Contoh: `http://192.168.19.1:8080`)*

---

## 📄 Lisensi

Proyek ini didistribusikan di bawah lisensi [MIT](LICENSE). Bebas digunakan, dimodifikasi, dan dikembangkan untuk keperluan pemantauan IoT dan fasilitas industri.
