"""
Server Proxy & Background Database Logger untuk Pos Pantau KP Dashboard.
- Menyajikan web dashboard lokal di port 8080 (tanpa hambatan CORS).
- Menangkap dan menyimpan seluruh data telemetri per hari ke SQLite database (monitoring.db).
- Menyediakan REST API riwayat harian dan ekspor CSV/Excel per hari.
"""
import http.server
import socketserver
import urllib.request
import urllib.parse
import sqlite3
import threading
import time
import datetime
import json
import os
import sys

PORT = 8080
TARGET_API = "http://192.168.18.113/api/data"
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(DIRECTORY, "monitoring.db")

# ========================================================
# 1. INISIALISASI DATABASE SQLITE
# ========================================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Tabel khusus Pos Pantau KP per hari
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kp_daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at TEXT NOT NULL,
            log_date TEXT NOT NULL,
            log_time TEXT NOT NULL,
            seq INTEGER,
            temp REAL,
            hum REAL,
            press REAL,
            pm25 REAL,
            pm10 REAL,
            last_update_str TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_kp_date ON kp_daily_logs(log_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_kp_recorded ON kp_daily_logs(recorded_at)')

    # Tabel snapshot lengkap seluruh zona (KP, Ruang Server, Genset)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS all_zones_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recorded_at TEXT NOT NULL,
            log_date TEXT NOT NULL,
            zone TEXT NOT NULL,
            seq INTEGER,
            temp REAL,
            hum REAL,
            press REAL,
            pm25 REAL,
            pm10 REAL,
            gas_iaq REAL,
            solar_persen REAL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_zone_date ON all_zones_logs(log_date, zone)')
    
    conn.commit()
    conn.close()
    print(f"[DATABASE] Terhubung ke SQLite: {DB_FILE}")

# ========================================================
# 2. BACKGROUND COLLECTOR THREAD (MENANGKAP DATA PER HARI)
# ========================================================
def background_collector():
    """Berjalan kontinu di background untuk menangkap data sensor ke database"""
    last_seq = None
    last_saved_time = 0
    poll_interval = 5  # polling setiap 5 detik

    print("[COLLECTOR] Background Data Logger aktif. Memantau " + TARGET_API)
    while True:
        try:
            req = urllib.request.Request(
                TARGET_API,
                headers={'User-Agent': 'Nexus-Monitor-Collector/2.0', 'Accept': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                content = response.read()
                data = json.loads(content.decode('utf-8'))
                
                kp = data.get("kp", {})
                current_seq = kp.get("seq")
                now = datetime.datetime.now()
                now_str = now.strftime('%Y-%m-%d %H:%M:%S')
                today_str = now.strftime('%Y-%m-%d')
                time_str = now.strftime('%H:%M:%S')

                # Simpan jika ada paket sequence baru ATAU jika sudah lewat 60 detik
                time_since_last = time.time() - last_saved_time
                if (current_seq is not None and current_seq != last_seq) or time_since_last >= 60:
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()

                    # 1. Simpan Pos Pantau KP
                    cursor.execute('''
                        INSERT INTO kp_daily_logs (
                            recorded_at, log_date, log_time, seq, temp, hum, press, pm25, pm10, last_update_str
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        now_str,
                        today_str,
                        time_str,
                        current_seq,
                        kp.get("temp"),
                        kp.get("hum"),
                        kp.get("press"),
                        kp.get("pm25"),
                        kp.get("pm10"),
                        kp.get("last_update")
                    ))

                    # 2. Simpan snapshot zona lainnya
                    server = data.get("Ruang Server", {})
                    if server:
                        cursor.execute('''
                            INSERT INTO all_zones_logs (
                                recorded_at, log_date, zone, temp, hum, press, gas_iaq
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            now_str, today_str, 'Ruang Server',
                            server.get("suhu"), server.get("kelembapan"), server.get("tekanan"), server.get("gas_iaq")
                        ))

                    genset = data.get("Ruang Genset Gedung Utama", {})
                    if genset:
                        cursor.execute('''
                            INSERT INTO all_zones_logs (
                                recorded_at, log_date, zone, temp, hum, solar_persen
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            now_str, today_str, 'Ruang Genset Gedung Utama',
                            genset.get("suhu"), genset.get("kelembapan"), genset.get("solar_persen")
                        ))

                    conn.commit()
                    conn.close()

                    last_seq = current_seq
                    last_saved_time = time.time()
                    print(f"[DB LOG {time_str}] Simpan data: Seq #{current_seq} | PM2.5: {kp.get('pm25')} | PM10: {kp.get('pm10')} | Suhu: {kp.get('temp')}°C")

        except Exception as e:
            # Jika alat mati/jaringan putus, tunggu dan coba lagi tanpa membuat crash
            pass

        time.sleep(poll_interval)

# ========================================================
# 3. HTTP HANDLER (DASHBOARD, PROXY & DATABASE API)
# ========================================================
class CustomHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # --------------------------------------------------------
        # A. PROXY REAL-TIME /api/data
        # --------------------------------------------------------
        if path == '/api/data':
            try:
                req = urllib.request.Request(
                    TARGET_API,
                    headers={'User-Agent': 'Nexus-Monitor/2.0', 'Accept': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    content = response.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
                    self.end_headers()
                    self.wfile.write(content)
            except Exception as e:
                self.send_response(502)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                err_json = f'{{"error": "Gagal menghubungi sensor {TARGET_API}", "details": "{str(e)}"}}'
                self.wfile.write(err_json.encode('utf-8'))
            return

        # --------------------------------------------------------
        # B. API DAFTAR TANGGAL DALAM DATABASE /api/db/dates
        # --------------------------------------------------------
        if path == '/api/db/dates':
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        log_date, 
                        COUNT(*) as total_records,
                        MIN(log_time) as first_time,
                        MAX(log_time) as last_time
                    FROM kp_daily_logs
                    GROUP BY log_date
                    ORDER BY log_date DESC
                ''')
                rows = cursor.fetchall()
                conn.close()

                dates_list = []
                for r in rows:
                    dates_list.append({
                        "date": r[0],
                        "total_records": r[1],
                        "first_time": r[2],
                        "last_time": r[3]
                    })

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(dates_list).encode('utf-8'))
            except Exception as e:
                self.send_error(500, f"Database Error: {e}")
            return

        # --------------------------------------------------------
        # C. API RIWAYAT HARIAN /api/db/history?date=YYYY-MM-DD
        # --------------------------------------------------------
        if path == '/api/db/history':
            target_date = query_params.get('date', [datetime.datetime.now().strftime('%Y-%m-%d')])[0]
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                
                # Hitung statistik harian
                cursor.execute('''
                    SELECT 
                        COUNT(*),
                        ROUND(AVG(pm25), 2), MAX(pm25), MIN(pm25),
                        ROUND(AVG(pm10), 2), MAX(pm10), MIN(pm10),
                        ROUND(AVG(temp), 2), MAX(temp), MIN(temp),
                        ROUND(AVG(hum), 2), MAX(hum), MIN(hum),
                        ROUND(AVG(press), 2)
                    FROM kp_daily_logs
                    WHERE log_date = ?
                ''', (target_date,))
                st = cursor.fetchone()

                # Ambil data logs (terbaru duluan, dibatasi 500 baris untuk performa)
                cursor.execute('''
                    SELECT id, recorded_at, log_time, seq, temp, hum, press, pm25, pm10
                    FROM kp_daily_logs
                    WHERE log_date = ?
                    ORDER BY id DESC
                    LIMIT 500
                ''', (target_date,))
                records = cursor.fetchall()
                conn.close()

                result = {
                    "date": target_date,
                    "total_records": st[0] or 0,
                    "stats": {
                        "avg_pm25": st[1], "max_pm25": st[2], "min_pm25": st[3],
                        "avg_pm10": st[4], "max_pm10": st[5], "min_pm10": st[6],
                        "avg_temp": st[7], "max_temp": st[8], "min_temp": st[9],
                        "avg_hum": st[10], "max_hum": st[11], "min_hum": st[12],
                        "avg_press": st[13]
                    },
                    "records": [
                        {
                            "id": r[0],
                            "recorded_at": r[1],
                            "time": r[2],
                            "seq": r[3],
                            "temp": r[4],
                            "hum": r[5],
                            "press": r[6],
                            "pm25": r[7],
                            "pm10": r[8]
                        }
                        for r in records
                    ]
                }

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode('utf-8'))
            except Exception as e:
                self.send_error(500, f"Database Error: {e}")
            return

        # --------------------------------------------------------
        # D. EKSPOR LAPORAN CSV PER HARI /api/db/export-csv?date=YYYY-MM-DD
        # --------------------------------------------------------
        if path == '/api/db/export-csv':
            target_date = query_params.get('date', [datetime.datetime.now().strftime('%Y-%m-%d')])[0]
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT log_time, seq, pm25, pm10, temp, hum, press
                    FROM kp_daily_logs
                    WHERE log_date = ?
                    ORDER BY id ASC
                ''', (target_date,))
                rows = cursor.fetchall()
                conn.close()

                # Buat format CSV RFC-4180 ramah Microsoft Excel
                csv_lines = []
                csv_lines.append("No,Tanggal,Waktu,Seq Paket,PM 2.5 (ug/m3),PM 10 (ug/m3),Suhu (C),Kelembapan (%RH),Tekanan (hPa),Kategori Udara")

                for idx, r in enumerate(rows, 1):
                    waktu, seq, pm25, pm10, temp, hum, press = r
                    # Hitung kategori udara
                    kat = "Baik"
                    if pm25 > 55.4:
                        kat = "Tidak Sehat"
                    elif pm25 > 15.5:
                        kat = "Sedang"

                    csv_lines.append(f"{idx},{target_date},{waktu},{seq},{pm25},{pm10},{temp},{hum},{press},{kat}")

                csv_output = "\r\n".join(csv_lines)
                filename = f"laporan_pos_pantau_kp_{target_date}.csv"

                self.send_response(200)
                self.send_header('Content-Type', 'text/csv; charset=utf-8')
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                # Sertakan UTF-8 BOM agar Excel menampilkan aksen teks dengan benar
                self.wfile.write(b'\xef\xbb\xbf' + csv_output.encode('utf-8'))
            except Exception as e:
                self.send_error(500, f"CSV Export Error: {e}")
            return

        # --------------------------------------------------------
        # E. DEFAULT STATIC FILE HANDLER (index.html, dll)
        # --------------------------------------------------------
        super().do_GET()

    def log_message(self, format, *args):
        # Abaikan log polling harian agar konsol terminal tetap rapi
        if '/api/data' not in args[0] and '/api/db/' not in args[0]:
            super().log_message(format, *args)

# ========================================================
# 4. ENTRY POINT
# ========================================================
if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    
    # 1. Siapkan database SQLite
    init_db()

    # 2. Mulai background logger thread
    t = threading.Thread(target=background_collector, daemon=True)
    t.start()

    # 3. Mulai server web
    try:
        with socketserver.TCPServer(("", PORT), CustomHTTPHandler) as httpd:
            url = f"http://localhost:{PORT}"
            print("=" * 65)
            print("  NEXUS IOT • POS PANTAU KP SERVER + DATABASE LOGGER")
            print("=" * 65)
            print(f"  • Dashboard URL    : {url}")
            print(f"  • Target Sensor    : {TARGET_API}")
            print(f"  • Database File    : {DB_FILE}")
            print("  • Status Database  : MENANGKAP DATA PER HARI (AKTIF)")
            print("=" * 65)
            print("  Tekan Ctrl+C untuk menghentikan server.")
            print("=" * 65)
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
        sys.exit(0)
    except Exception as e:
        print(f"Gagal menjalankan server: {e}")
        sys.exit(1)
