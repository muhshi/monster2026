# MONSTER 2026 (MONItoring SE Ter-sembunyi 2026)

**MONSTER 2026** adalah sebuah tool scraping pintar berbasis Python yang dirancang secara spesifik untuk melakukan penarikan data Monitoring Progress Lapangan dan Pemetaan Pengawas secara otomatis dari Dashboard web FASIH (Flexible Authentic Survey Instrument in Harmony) BPS. Mengadopsi teknologi Selenium *Remote Debugging*, aplikasi ini beroperasi secara transparan dan "tersembunyi" dari deteksi bot server WAF Cloudflare.

## Fitur Utama

1. **Auto-Fetch Progress Pencacah**: Menarik status *Open, Submitted, Approved, Rejected* dari progres pencacah, dan menyimpannya ke MySQL (serta cadangan `.db` SQLite).
2. **Auto-Fetch Mapping Pengawas**: Mengambil data master pengawas (email pengawas untuk setiap wilayah) agar bisa dikawinkan ke data *progress*.
3. **Anti-Detection & CAPTCHA Handler**: Menggunakan metode Selenium yang mendompleng ke browser asli pengguna (*Remote Debugging Port*). Terdapat deteksi otomatis saat server menampilkan WAF/CAPTCHA, yang akan meminta pengguna untuk memverifikasi secara manual sebelum otomatis melanjutkan unduhan dari halaman yang tersisa, tanpa harus mengulang dari nol.
4. **Smart UPSERT**: Menyimpan data berdasar `id_sls`. Apabila data pada tanggal yang sama sudah ditarik, akan diperbarui/di-*replace* (mencegah redundansi duplikat data), namun riwayat tanggal penarikan sebelumnya tetap tersimpan utuh di sistem database.

---

## Prasyarat (*Requirements*)

- **Python 3.7+**
- **Google Chrome Browser**
- Library yang digunakan: `selenium`, `pymysql`, `sqlalchemy`

---

## 1. Instalasi dan Setup

1. **Clone repositori** ini:
   ```bash
   git clone https://github.com/saiful/se2026-monitoring.git
   cd se2026-monitoring/Lapangan
   ```

2. **Install dependency**:
   ```bash
   pip3 install -r requirements.txt
   # atau install manual jika belum ada file requirements
   pip3 install selenium pymysql sqlalchemy
   ```

3. **Konfigurasi Database & API**:
   Copy file `config.example.json` menjadi `config.json` dan sesuaikan parameter login `host`, `user`, dan `password` database MySQL kamu:

   ```bash
   cp config.example.json config.json
   ```

   Lalu edit file `config.json`:
   ```json
   {
     "database": {
       "engine": "mysql",
       "host": "10.133.21.24",
       "user": "root",
       "password": "password_kamu_disini",
       "database_name": "fasih",
       "sqlite_file": "monitoring_se2026.db"
     },
     "fasih_api": {
       "surveyPeriodId": "fd68e454-ba45-4b85-8205-f3bf777ded24",
       "roleIdPencacah": "6d7d919a-45e5-4779-bb87-2905b49fd31a",
       "roleIdPengawas": "93bcf446-c4c1-4462-8ed0-4b0f7ae89e52"
     }
   }
   ```
   *Catatan: Nilai ID untuk `surveyPeriodId` dll di atas adalah nilai default SE2026. Kamu tidak perlu mengubahnya kecuali server FASIH mengganti ID survei.*

---

## 2. Cara Menjalankan Program (Panduan Lengkap)

Program ini membutuhkan Chrome yang berjalan pada mode *remote debugging*. Oleh karena itu, langkah utamanya adalah: (1) Buka Chrome mode debug, lalu (2) Jalankan Script.

### **Pilihan A: Menjalankan Menggunakan File Script Runner (Sangat Disarankan)**

Untuk memudahkan eksekusi tanpa mengetik command panjang, kamu bisa langsung menjalankan *runner script* yang sudah disediakan.

- **Pengguna Mac/Linux**:
  Buka Terminal, masuk ke direktori folder Lapangan, lalu jalankan:
  ```bash
  ./run.sh
  ```
- **Pengguna Windows**:
  Klik ganda (`Double Click`) pada file **`run.bat`**

Ikuti instruksi interaktif yang tampil di layar.


### **Pilihan B: Menjalankan Secara Manual via Terminal**

**LANGKAH 1: Tutup Chrome yang Sedang Berjalan**
Matikan sepenuhnya aplikasi Google Chrome (jangan ada tab/jendela yang tersisa).

**LANGKAH 2: Buka Chrome dengan Mode Debugging**
- **Mac:**
  Buka terminal baru lalu eksekusi:
  ```bash
  /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 &
  ```
- **Windows:**
  Buka command prompt (CMD) dan jalankan:
  ```cmd
  "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-debug"
  ```

**LANGKAH 3: Login ke Web FASIH**
Pada jendela Chrome yang baru saja terbuka, navigasi ke website Single Sign-On BPS dan **Login** sampai kamu melihat layar **Dashboard utama**.

**LANGKAH 4: Eksekusi Script Penarikan**
Di terminal/CMD yang terpisah (jangan matikan Chrome), jalankan script ini:

```bash
# Untuk menarik mapping email pengawas (Jalankan sekali di awal atau jika ada perubahan petugas pengawas)
python3 fetch_pengawas.py

# Untuk menarik Progress harian SLS Pencacah (Jalankan rutin setiap hari)
python3 monitoring_lapangan.py
```

---

## 3. Menangani Masalah (Troubleshooting)

- **`Session not created: cannot connect to chrome at 127.0.0.1:9222`**
  **Penyebab:** Chrome mode debugging gagal terbuka, atau kamu membuka Chrome normal *sebelum* menjalankan command `--remote-debugging-port`.
  **Solusi:** Kill paksa (`pkill -f "Google Chrome"`) semua Chrome yang ada di task manager, lalu buka ulang Chrome lewat terminal yang sudah dicantumkan di Langkah 2.
- **Kosongnya Sebagian Email Pengawas**
  Saat pencacah di-*fetch*, script akan menengok *lookup file* `pengawas_mapping.json`. Pastikan file tersebut aktual dengan menjalankan script `python3 fetch_pengawas.py` terlebih dahulu jika dirasa ada pengawas yang kurang.
### Menangani Penolakan Server (CAPTCHA Terdeteksi / WAF Cloudflare)

Website FASIH dilindungi oleh sistem keamanan Cloudflare (WAF) yang membatasi jumlah request (*Rate Limiting*). Jika script mendeteksi bahwa IP-mu diblokir sementara dan dilempar ke halaman validasi CAPTCHA, program ini **tidak akan *crash* atau keluar**, melainkan akan masuk ke mode "Jeda Interaktif" (Pause).

**Apa yang harus kamu lakukan jika terkena CAPTCHA?**
1. Jendela terminalmu akan berbunyi dan menampilkan peringatan tebal: `⚠️ CAPTCHA TERDETEKSI!`.
2. Segera buka jendela Chrome yang dibuat oleh script (Chrome debugging yang terbuka otomatis sebelumnya).
3. Di sana, kamu akan melihat halaman peringatan Cloudflare/CAPTCHA ("Verify you are human").
4. Klik/centang kotak CAPTCHA tersebut secara manual layaknya manusia biasa hingga berhasil masuk kembali ke dashboard.
5. Kembali ke jendela Terminal, lalu **tekan tombol `ENTER`**.
6. Ajaib! Python akan langsung melanjutkan proses pengunduhan (*resume*) tepat dari halaman terakhir yang sempat terputus tanpa ada satu pun data yang terlewat.

---
## Changelog

- **Added**: Fitur auto-capture dan penyimpanan `status_draft` ke dalam skema tabel database `monitoring_se2026` lengkap dengan *auto-migration* kolom secara otomatis.
- **Added**: Implementasi `run.sh` dan `run.bat` untuk mempermudah operasional end-user.
- **Added**: Interaktif CAPTCHA Solver *wait mechanism* via Selenium yang menjeda proses perulangan selagi user merampungkan verifikasi Human-Cloudflare.
- **Changed**: Peralihan dari Request Library API langsung ke implementasi eksekusi `fetch()` JS payload secara native di dalam *local session browser* (menggunakan `execute_async_script()`).
- **Fixed**: Mengembalikan Size Fetch Page ke Size default `5` per *request body* untuk mencegah `HTTP 400 Bad Request` dari WAF BPS.
- **Fixed**: Penghapusan manual cookie XSRF di `config.json` karena Script Selenium saat ini sudah diatur mampu melakukan token scrapping dinamis dari Document Cookie browser berjalan.
- **Fixed**: Menambahkan flag `--user-data-dir` pada eksekusi Google Chrome di `run.bat` dan panduan README agar fitur *remote debugging* pada Windows berfungsi meski ada Chrome lain yang sedang aktif.
- **Changed (24 Juni 2026)**: Mengganti WebDriver Chrome standar dengan `undetected_chromedriver` (dikonfigurasi untuk Chrome v149) pada `monitoring_lapangan.py` guna menghindari deteksi WAF/bot block.
- **Changed (24 Juni 2026)**: Memperbesar jeda antar request (*sleep time*) dari 1-3 detik menjadi 4-8 detik secara acak untuk mengurangi risiko terpicu oleh *rate limiting* WAF.
- **Added (24 Juni 2026)**: Membuat script migrasi `migrate_tanggal_datetime.py` untuk mengubah tipe data kolom `tanggal_tarik` dari `DATE` menjadi `DATETIME`.
- **Changed (24 Juni 2026)**: Memperbarui penulisan format tanggal di `monitoring_lapangan.py` agar menyimpan waktu detail (YYYY-MM-DD HH:MM:SS) sehingga data lawas tetap aman dan data baru tercatat dengan timestamp lengkap.
- **Added (24 Juni 2026)**: Menambahkan pengecekan tipe kolom di `migrate_tanggal_datetime.py` agar dilewati jika kolom `tanggal_tarik` sudah bertipe `DATETIME` atau tabel belum terbentuk.
- **Added (24 Juni 2026)**: Mengintegrasikan eksekusi migrasi otomatis pada berkas `run.bat` dan `run.sh` saat program pertama kali dibuka.
- **Fixed (25 Juni 2026)**: Mengubah format `current_date` di `monitoring_lapangan.py` dari full DATETIME (`%Y-%m-%d %H:%M:%S`) ke DATE-only (`%Y-%m-%d`) agar mekanisme UPSERT per hari berjalan benar (sebelumnya setiap run membuat row baru karena detik berbeda).
- **Fixed (25 Juni 2026)**: Memperbaiki UNIQUE KEY tabel `monitoring_se2026` dari `(tanggal_tarik, region_code)` menjadi `(tanggal_tarik, region_code, email_pencacah)` agar data setiap pencacah per wilayah per hari tersimpan sebagai baris tersendiri dan tidak saling overwrite.
- **Added (25 Juni 2026)**: Membuat script `migrate_monitoring_schema.py` untuk migrasi skema DB existing (ubah `tanggal_tarik` DATETIME→DATE dan perbaiki UNIQUE KEY) tanpa menghapus data.
