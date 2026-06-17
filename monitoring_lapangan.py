import json
import time
import os
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ========================================
# Monitoring Lapangan SE2026 (Selenium)
# ========================================
# Script ini menggunakan Selenium agar Cloudflare
# tidak mendeteksinya sebagai bot.
#
# Alur:
# 1. Buka Chrome -> Login FASIH manual
# 2. Tekan Enter di terminal
# 3. Script otomatis menarik data & simpan ke DB
# ========================================

def load_config():
    if not os.path.exists('config.json'):
        print("Error: config.json tidak ditemukan!")
        exit(1)
    with open('config.json', 'r') as f:
        return json.load(f)

def init_db(config):
    db_cfg = config['database']
    engine = db_cfg.get('engine', 'mysql').lower()
    
    if engine == 'sqlite':
        import sqlite3
        db_file = db_cfg.get('sqlite_file', 'monitoring_se2026.db')
        print(f"Menggunakan SQLite: {db_file}")
        connection = sqlite3.connect(db_file)
        cursor = connection.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS monitoring_se2026 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal_tarik DATE,
            region_code VARCHAR(20),
            email_pencacah VARCHAR(100),
            email_pengawas VARCHAR(100),
            total_beban INT,
            status_open INT DEFAULT 0,
            status_draft INT DEFAULT 0,
            status_submitted INT DEFAULT 0,
            status_approved INT DEFAULT 0,
            status_rejected INT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (tanggal_tarik, region_code)
        )
        """
        cursor.execute(create_table_query)
        # Auto-migrate: Tambahkan kolom status_draft jika belum ada di tabel lama
        try:
            cursor.execute("ALTER TABLE monitoring_se2026 ADD COLUMN status_draft INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        connection.commit()
        return connection, 'sqlite'
        
    elif engine == 'mysql':
        import mysql.connector
        print("Menggunakan MySQL...")
        connection = mysql.connector.connect(
            host=db_cfg['host'],
            database=db_cfg['database_name'],
            user=db_cfg['user'],
            password=db_cfg['password']
        )
        cursor = connection.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS monitoring_se2026 (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            tanggal_tarik DATE,
            region_code VARCHAR(20),
            email_pencacah VARCHAR(100),
            email_pengawas VARCHAR(100),
            total_beban INT,
            status_open INT DEFAULT 0,
            status_draft INT DEFAULT 0,
            status_submitted INT DEFAULT 0,
            status_approved INT DEFAULT 0,
            status_rejected INT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_daily_region (tanggal_tarik, region_code)
        )
        """
        cursor.execute(create_table_query)
        # Auto-migrate: Tambahkan kolom status_draft jika belum ada di tabel lama
        try:
            cursor.execute("ALTER TABLE monitoring_se2026 ADD COLUMN status_draft INT DEFAULT 0 AFTER status_open")
        except mysql.connector.Error:
            pass
        connection.commit()
        return connection, 'mysql'
    else:
        print("Engine database tidak dikenali di config.json")
        exit(1)

def open_browser_and_login():
    """Buka Chrome dan tunggu user login manual."""
    print("\n" + "="*60)
    print("  MEMBUKA BROWSER CHROME...")
    print("="*60)
    
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_experimental_option("detach", True)
    
    driver = webdriver.Chrome(options=chrome_options)
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    })
    
    driver.get("https://fasih-sm.bps.go.id")
    time.sleep(5)
    
    print(f"\n[DEBUG] URL saat ini: {driver.current_url}")
    print(f"[DEBUG] Title: {driver.title}")
    
    print("\n" + "="*60)
    print("  INSTRUKSI:")
    print("  1. Login ke FASIH di browser yang terbuka")
    print("  2. Pastikan sudah masuk ke halaman dashboard")
    print("  3. Kembali ke terminal ini")
    print("  4. Tekan ENTER untuk mulai menarik data")
    print("="*60)
    input("\n>>> Tekan ENTER setelah login berhasil... ")
    
    print(f"\n[DEBUG] URL setelah login: {driver.current_url}")
    
    # Cek XSRF-TOKEN
    cookies = driver.get_cookies()
    for c in cookies:
        if c['name'] == 'XSRF-TOKEN':
            print(f"[DEBUG] XSRF-TOKEN: {c['value'][:20]}...")
            break
    
    return driver

def fetch_page_selenium(driver, page_num, config, max_retries=3):
    """Gunakan fetch() dari dalam browser untuk memanggil API."""
    api_cfg = config['fasih_api']
    
    payload = {
        "surveyPeriodId": api_cfg['surveyPeriodId'],
        "surveyRoleId": api_cfg['roleIdPencacah'],
        "size": 5,
        "page": page_num,
        "search": "",
        "target": "TARGET_ONLY",
        "region": {
            "region1Id": None, "region2Id": None, "region3Id": None, 
            "region4Id": None, "region5Id": None, "region6Id": None, 
            "region7Id": None, "region8Id": None, "region9Id": None, "region10Id": None
        },
        "regionSummaryLevel": 6
    }
    
    # JavaScript: fetch lalu kembalikan raw text + status (bukan langsung .json())
    # supaya kita bisa mendeteksi CAPTCHA HTML response
    js_script = """
    var callback = arguments[arguments.length - 1];
    var payload = arguments[0];
    
    var xsrfToken = '';
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var cookie = cookies[i].trim();
        if (cookie.startsWith('XSRF-TOKEN=')) {
            xsrfToken = decodeURIComponent(cookie.substring('XSRF-TOKEN='.length));
            break;
        }
    }
    
    fetch('/app/api/analytic/api/v2/assignment/report-progress-by-responsibility', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'X-XSRF-TOKEN': xsrfToken
        },
        body: JSON.stringify(payload),
        credentials: 'same-origin'
    })
    .then(function(response) {
        return response.text().then(function(text) {
            callback({status: response.status, body: text});
        });
    })
    .catch(function(err) {
        callback({error: err.message || err.toString()});
    });
    """
    
    for attempt in range(1, max_retries + 1):
        try:
            driver.set_script_timeout(120)
            result = driver.execute_async_script(js_script, payload)
            
            if result is None:
                print("  Response kosong dari browser.")
                return None
            
            if "error" in result:
                print(f"  Fetch error: {result['error']}")
                return None
            
            status = result.get("status", 0)
            body = result.get("body", "")
            
            # Deteksi CAPTCHA / HTML response
            if "<!DOCTYPE" in body or "<html>" in body.lower() or "captcha" in body.lower():
                print("\n" + "!"*60)
                print("  ⚠️  CAPTCHA TERDETEKSI!")
                print("  Buka browser dan selesaikan CAPTCHA-nya.")
                print("  Setelah selesai, kembali ke sini.")
                print("!"*60)
                input("  >>> Tekan ENTER setelah CAPTCHA diselesaikan... ")
                print(f"  Mencoba ulang page {page_num}...")
                # Navigasi kembali ke halaman FASIH (agar context browser benar)
                driver.get("https://fasih-sm.bps.go.id")
                time.sleep(3)
                continue
            
            # Server error - retry otomatis
            if status >= 500 and attempt < max_retries:
                wait = attempt * 5
                print(f"  Server error ({status}). Retry {attempt}/{max_retries} dalam {wait} detik...")
                time.sleep(wait)
                continue
            
            if status != 200:
                print(f"  HTTP error: {status}")
                return None
            
            # Parse JSON
            try:
                import json as json_mod
                data = json_mod.loads(body)
                if "data" in data and "content" in data["data"]:
                    return data["data"]
                return None
            except Exception as parse_err:
                print(f"  JSON parse error: {parse_err}")
                return None
                
        except Exception as e:
            if attempt < max_retries:
                wait = attempt * 5
                print(f"  Exception: {e}. Retry {attempt}/{max_retries} dalam {wait} detik...")
                time.sleep(wait)
                continue
            print(f"  Error: {e}")
            return None
    
    return None

def process_and_save(connection, engine_type, page_data, current_date):
    if not page_data or "content" not in page_data:
        return 0
        
    content = page_data["content"]
    rows_to_insert = []
    
    for item in content:
        email_pencacah = item.get("email", "")
        region_summary = item.get("regionSummary", [])
        
        for region in region_summary:
            region_code = region.get("regionCode", "")
            total_beban = region.get("total", 0)
            
            status_open = 0
            status_draft = 0
            status_submitted = 0
            status_approved = 0
            status_rejected = 0
            
            status_breakdown = region.get("statusBreakdown", [])
            for st in status_breakdown:
                status_name = st.get("status", "").upper()
                count = st.get("count", 0)
                
                if "OPEN" in status_name:
                    status_open = count
                elif "DRAFT" in status_name:
                    status_draft = count
                elif "SUBMITTED" in status_name:
                    status_submitted = count
                elif "COMPLETED" in status_name or "APPROVED" in status_name:
                    status_approved = count
                elif "REJECTED" in status_name:
                    status_rejected = count
            
            rows_to_insert.append((
                current_date, region_code, email_pencacah, 
                total_beban, status_open, status_draft, status_submitted, status_approved, status_rejected
            ))
            
    if rows_to_insert:
        try:
            cursor = connection.cursor()
            if engine_type == 'mysql':
                upsert_query = """
                INSERT INTO monitoring_se2026 (
                    tanggal_tarik, region_code, email_pencacah,
                    total_beban, status_open, status_draft, status_submitted, status_approved, status_rejected
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    email_pencacah = VALUES(email_pencacah),
                    total_beban = VALUES(total_beban),
                    status_open = VALUES(status_open),
                    status_draft = VALUES(status_draft),
                    status_submitted = VALUES(status_submitted),
                    status_approved = VALUES(status_approved),
                    status_rejected = VALUES(status_rejected)
                """
            else:
                upsert_query = """
                INSERT INTO monitoring_se2026 (
                    tanggal_tarik, region_code, email_pencacah,
                    total_beban, status_open, status_draft, status_submitted, status_approved, status_rejected
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tanggal_tarik, region_code) DO UPDATE SET
                    email_pencacah = excluded.email_pencacah,
                    total_beban = excluded.total_beban,
                    status_open = excluded.status_open,
                    status_draft = excluded.status_draft,
                    status_submitted = excluded.status_submitted,
                    status_approved = excluded.status_approved,
                    status_rejected = excluded.status_rejected
                """
            cursor.executemany(upsert_query, rows_to_insert)
            connection.commit()
            return len(rows_to_insert)
        except Exception as e:
            print(f"Error inserting/updating rows: {e}")
            return 0
    return 0

def main():
    config = load_config()
    
    # Buka browser dan login
    driver = open_browser_and_login()
    
    # Hubungkan ke database
    print("\nMenghubungkan ke Database...")
    connection, engine_type = init_db(config)
    
    try:
        current_date = datetime.now().strftime('%Y-%m-%d')
        page = 0
        total_records_inserted = 0
        
        print(f"\nMulai menarik data progres (Pencacah) untuk tanggal: {current_date}")
        print("-" * 50)
        
        while True:
            print(f"Fetching page {page}...")
            page_data = fetch_page_selenium(driver, page, config)
            
            if not page_data:
                print("Gagal mengambil data. Kemungkinan session expired.")
                break
                
            content = page_data.get("content", [])
            if not content:
                print("Data content kosong. Semua halaman telah diproses.")
                break
                
            inserted = process_and_save(connection, engine_type, page_data, current_date)
            total_records_inserted += inserted
            print(f" -> Berhasil memproses {inserted} wilayah ke database (Upsert).")
            
            if page_data.get("last", True):
                print("Mencapai halaman terakhir. ✓")
                break
                
            page += 1
            # Jeda kecil antar request (tidak perlu lama karena ini dari browser asli)
            sleep_time = random.uniform(1, 3)
            time.sleep(sleep_time)
            
        print(f"\n{'='*50}")
        print(f"  SELESAI! Total {total_records_inserted} data monitoring diproses.")
        print(f"{'='*50}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'connection' in locals():
            try:
                connection.close()
                print("Koneksi Database ditutup.")
            except:
                pass
        # TIDAK menutup browser karena ini Chrome milik user
        print("Selesai. Browser tetap terbuka.")

if __name__ == "__main__":
    main()
