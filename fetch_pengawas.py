import json
import time
import os
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ========================================
# Fetch Pengawas Mapping (Selenium)
# ========================================
# Script ini menarik data pemetaan Pengawas
# menggunakan Selenium agar tidak kena blokir.
#
# Cukup jalankan SEKALI saja, kecuali ada
# pergantian petugas.
# ========================================

def load_config():
    if not os.path.exists('config.json'):
        print("Error: config.json tidak ditemukan!")
        exit(1)
    with open('config.json', 'r') as f:
        return json.load(f)

def open_browser_and_login():
    """Sambungkan ke Chrome yang sudah terbuka via remote debugging port."""
    print("\n" + "="*60)
    print("  MENGHUBUNGKAN KE BROWSER CHROME...")
    print("="*60)
    print("\n  Pastikan Chrome sudah dibuka dengan perintah:")
    print("  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
    print()
    
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"\n  ❌ Gagal menyambung ke Chrome: {e}")
        print("  Pastikan Chrome sudah dibuka dengan --remote-debugging-port=9222")
        exit(1)
    
    print(f"\n[DEBUG] URL saat ini : {driver.current_url}")
    print(f"[DEBUG] Title halaman: {driver.title}")
    
    # Cek apakah sudah login atau berada di tab yang salah
    current_url = driver.current_url.lower()
    
    if "new-tab-page" in current_url or "chrome://" in current_url:
        print("\n  ⚠️ PERHATIAN: Tab aktif kamu saat ini adalah 'New Tab' kosong!")
        print("  Browser akan menolak script jika tidak berada di halaman web BPS.")
        print("  Silakan ketik manual 'fasih-sm.bps.go.id' di address bar, lalu login.")
        input("\n>>> Tekan ENTER setelah kamu membuka FASIH dan login... ")
        current_url = driver.current_url.lower()

    if "sso.bps.go.id" in current_url or "login" in current_url:
        print("\n  Kamu belum login. Silakan login dulu di browser.")
        input("\n>>> Tekan ENTER setelah login berhasil... ")
        print(f"\n[DEBUG] URL setelah login : {driver.current_url}")
    
    return driver

def fetch_page_selenium(driver, page_num, config, max_retries=3):
    """Gunakan fetch() dari dalam browser untuk memanggil API."""
    api_cfg = config['fasih_api']
    
    payload = {
        "surveyPeriodId": api_cfg['surveyPeriodId'],
        "surveyRoleId": api_cfg['roleIdPengawas'],
        "size": 10,
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
            
            if "<!DOCTYPE" in body or "<html>" in body.lower() or "captcha" in body.lower():
                print("\n" + "!"*60)
                print("  ⚠️  CAPTCHA TERDETEKSI!")
                print("  Buka browser dan selesaikan CAPTCHA-nya.")
                print("  Setelah selesai, kembali ke sini.")
                print("!"*60)
                input("  >>> Tekan ENTER setelah CAPTCHA diselesaikan... ")
                print(f"  Mencoba ulang page {page_num}...")
                driver.get("https://fasih-sm.bps.go.id")
                time.sleep(3)
                continue
            
            if status >= 500 and attempt < max_retries:
                wait = attempt * 5
                print(f"  Server error ({status}). Retry {attempt}/{max_retries} dalam {wait} detik...")
                time.sleep(wait)
                continue
            
            if status != 200:
                print(f"  HTTP error: {status}")
                return None
            
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

def main():
    config = load_config()
    
    # Buka browser dan login
    driver = open_browser_and_login()
    
    import mysql.connector
    try:
        db_cfg = config['database']
        connection = mysql.connector.connect(
            host=db_cfg['host'],
            user=db_cfg['user'],
            password=db_cfg['password'],
            database=db_cfg['database_name']
        )
    except Exception as e:
        print(f"Gagal koneksi database: {e}")
        return

    page = 0
    total_processed = 0
    
    print("\nMulai menarik master data Pengawas...")
    print("-" * 50)
    
    try:
        with connection.cursor() as cursor:
            # Create table if not exists
            create_tbl = """
            CREATE TABLE IF NOT EXISTS alokasi_pengawas (
                region_code VARCHAR(20) PRIMARY KEY,
                email_pengawas VARCHAR(100),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
            cursor.execute(create_tbl)
            connection.commit()
            
            while True:
                print(f"Fetching Pengawas page {page}...")
                page_data = fetch_page_selenium(driver, page, config)
                
                if not page_data:
                    print("Gagal mengambil data. Kemungkinan session expired.")
                    break
                    
                content = page_data.get("content", [])
                if not content:
                    print("Data content kosong. Semua halaman telah diproses.")
                    break
                    
                for item in content:
                    email = item.get("email", "")
                    for region in item.get("regionSummary", []):
                        region_code = region.get("regionCode", "")
                        
                        # Simpan langsung ke database
                        sql = """
                        INSERT INTO alokasi_pengawas (region_code, email_pengawas)
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE email_pengawas = VALUES(email_pengawas)
                        """
                        cursor.execute(sql, (region_code, email))
                        total_processed += 1
                
                connection.commit()
                print(f" -> Halaman {page}: {len(content)} pengawas diproses.")
                
                if page_data.get("last", True):
                    print("Mencapai halaman terakhir. ✓")
                    break
                    
                page += 1
                # Jeda diperbesar agar tidak terdeteksi rate-limiting WAF
                sleep_time = random.uniform(4, 8)
                time.sleep(sleep_time)
            
            print(f"\n{'='*50}")
            print(f"  SELESAI! {total_processed} pemetaan Pengawas disimpan")
            print(f"  ke tabel: alokasi_pengawas")
            print(f"{'='*50}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'connection' in locals():
            connection.close()
        # TIDAK menutup browser karena ini Chrome milik user
        print("Selesai. Browser tetap terbuka.")

if __name__ == "__main__":
    main()
