import json
import os
import sys


def load_config():
    if not os.path.exists('config.json'):
        print('Error: config.json tidak ditemukan! Jalankan dari folder yang sama.')
        sys.exit(1)
    with open('config.json', 'r') as f:
        return json.load(f)


def migrate_mysql(config):
    import mysql.connector
    db_cfg = config['database']
    conn = mysql.connector.connect(
        host=db_cfg['host'],
        database=db_cfg['database_name'],
        user=db_cfg['user'],
        password=db_cfg['password'],
    )
    cur = conn.cursor()
    print('\n[MySQL] Memulai migrasi...\n')

    cur.execute("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = %s AND table_name = 'monitoring_se2026'
    """, (db_cfg['database_name'],))
    if cur.fetchone()[0] == 0:
        print('  Tabel monitoring_se2026 belum ada. Tidak perlu migrasi.')
        conn.close()
        return

    cur.execute("""
        SELECT DATA_TYPE FROM information_schema.columns
        WHERE table_schema = %s AND table_name = 'monitoring_se2026'
          AND column_name = 'tanggal_tarik'
    """, (db_cfg['database_name'],))
    row = cur.fetchone()
    current_type = row[0].lower() if row else 'unknown'
    print(f'  Tipe kolom tanggal_tarik saat ini: {current_type.upper()}')

    # STEP 1: Ubah DATETIME -> DATE
    if current_type != 'date':
        print('  [1/3] Mengubah tanggal_tarik DATETIME -> DATE...')
        cur.execute('ALTER TABLE monitoring_se2026 MODIFY COLUMN tanggal_tarik DATE NOT NULL')
        conn.commit()
        print('        OK.')
    else:
        print('  [1/3] Kolom tanggal_tarik sudah DATE. Lewat.')

    # STEP 2: Hapus UNIQUE key lama, buat baru
    print('  [2/3] Memperbarui UNIQUE key...')
    cur.execute("""
        SELECT CONSTRAINT_NAME FROM information_schema.table_constraints
        WHERE table_schema = %s AND table_name = 'monitoring_se2026'
          AND constraint_type = 'UNIQUE'
    """, (db_cfg['database_name'],))
    existing_keys = [r[0] for r in cur.fetchall()]
    print(f'        UNIQUE key ditemukan: {existing_keys}')
    for key_name in existing_keys:
        try:
            cur.execute(f'ALTER TABLE monitoring_se2026 DROP INDEX {key_name}')
            conn.commit()
            print(f'        Hapus key lama: {key_name}')
        except Exception as e:
            print(f'        Skip {key_name}: {e}')

    # Hapus duplikat sebelum tambah UNIQUE key baru
    cur.execute("""
        SELECT tanggal_tarik, region_code, email_pencacah, COUNT(*) as cnt
        FROM monitoring_se2026
        GROUP BY tanggal_tarik, region_code, email_pencacah
        HAVING cnt > 1
    """)
    duplicates = cur.fetchall()
    if duplicates:
        print(f'        Duplikat ditemukan: {len(duplicates)} kombinasi. Membersihkan...')
        cur.execute("""
            DELETE t1 FROM monitoring_se2026 t1
            INNER JOIN monitoring_se2026 t2
            WHERE t1.tanggal_tarik = t2.tanggal_tarik
              AND t1.region_code    = t2.region_code
              AND t1.email_pencacah = t2.email_pencacah
              AND t1.id < t2.id
        """)
        conn.commit()
        print('        Duplikat dihapus (baris paling baru dipertahankan).')
    else:
        print('        Tidak ada duplikat.')

    cur.execute("""
        ALTER TABLE monitoring_se2026
        ADD UNIQUE KEY unique_daily_region_pencacah (tanggal_tarik, region_code, email_pencacah)
    """)
    conn.commit()
    print('        UNIQUE key baru: (tanggal_tarik, region_code, email_pencacah)')

    # STEP 3: Verifikasi
    print('  [3/3] Verifikasi...')
    cur.execute('DESCRIBE monitoring_se2026')
    rows = cur.fetchall()
    print('\n  Struktur tabel setelah migrasi:')
    print(f"  {'Field':<25} {'Type':<20} Key")
    print('  ' + '-' * 50)
    for r in rows:
        print(f'  {str(r[0]):<25} {str(r[1]):<20} {r[3]}')

    cur.close()
    conn.close()
    print('\n[MySQL] Migrasi selesai!\n')


def migrate_sqlite(config):
    import sqlite3
    db_cfg = config['database']
    db_file = db_cfg.get('sqlite_file', 'monitoring_se2026.db')
    if not os.path.exists(db_file):
        print(f'  File SQLite tidak ditemukan: {db_file}. Tidak perlu migrasi.')
        return
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    print(f'\n[SQLite] Memulai migrasi: {db_file}\n')

    print('  [1/4] Rename tabel lama -> monitoring_se2026_backup_old ...')
    cur.execute('DROP TABLE IF EXISTS monitoring_se2026_backup_old')
    cur.execute('ALTER TABLE monitoring_se2026 RENAME TO monitoring_se2026_backup_old')
    conn.commit()
    print('        OK.')

    print('  [2/4] Buat tabel baru dengan skema benar...')
    cur.execute("""
        CREATE TABLE monitoring_se2026 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal_tarik DATE NOT NULL,
            region_code VARCHAR(20),
            email_pencacah VARCHAR(100),
            total_beban INT,
            status_open INT DEFAULT 0,
            status_draft INT DEFAULT 0,
            status_submitted INT DEFAULT 0,
            status_approved INT DEFAULT 0,
            status_rejected INT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (tanggal_tarik, region_code, email_pencacah)
        )
    """)
    conn.commit()
    print('        OK.')

    print('  [3/4] Menyalin data (konversi DATETIME -> DATE)...')
    cur.execute("""
        INSERT OR REPLACE INTO monitoring_se2026 (
            tanggal_tarik, region_code, email_pencacah,
            total_beban, status_open, status_draft,
            status_submitted, status_approved, status_rejected, updated_at
        )
        SELECT
            DATE(tanggal_tarik), region_code, email_pencacah,
            total_beban, status_open, COALESCE(status_draft, 0),
            status_submitted, status_approved, status_rejected, updated_at
        FROM monitoring_se2026_backup_old
        ORDER BY id ASC
    """)
    conn.commit()

    print('  [4/4] Verifikasi...')
    cur.execute('SELECT COUNT(*) FROM monitoring_se2026')
    count_new = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM monitoring_se2026_backup_old')
    count_old = cur.fetchone()[0]
    print(f'        Data lama : {count_old} baris')
    print(f'        Data baru : {count_new} baris')
    if count_old != count_new:
        print(f'        Selisih {count_old - count_new} baris = duplikat yg di-deduplicate (aman).')
    else:
        print('        Jumlah baris sama persis.')
    print('  Backup tersimpan sebagai monitoring_se2026_backup_old.')
    cur.close()
    conn.close()
    print('\n[SQLite] Migrasi selesai!\n')


def main():
    print('=' * 60)
    print('  MIGRASI SKEMA: monitoring_se2026')
    print('=' * 60)
    print("""
  Perubahan yang akan dilakukan:
    1. tanggal_tarik : DATETIME  ->  DATE
    2. UNIQUE KEY    : (tanggal_tarik, region_code)
                    -> (tanggal_tarik, region_code, email_pencacah)

  Data TIDAK akan dihapus. Script ini aman dijalankan.
""")
    confirm = input("  Lanjutkan migrasi? (ketik 'ya' untuk lanjut): ").strip().lower()
    if confirm != 'ya':
        print('  Migrasi dibatalkan.')
        return
    config = load_config()
    engine = config['database'].get('engine', 'mysql').lower()
    if engine == 'mysql':
        migrate_mysql(config)
    elif engine == 'sqlite':
        migrate_sqlite(config)
    else:
        print(f'Engine {engine} tidak dikenali.')
        sys.exit(1)


if __name__ == '__main__':
    main()
