import json
import os

def load_config():
    if not os.path.exists('config.json'):
        print("Error: config.json tidak ditemukan!")
        exit(1)
    with open('config.json', 'r') as f:
        return json.load(f)

def run_migration():
    config = load_config()
    db_cfg = config['database']
    engine = db_cfg.get('engine', 'mysql').lower()

    if engine == 'sqlite':
        db_file = db_cfg.get('sqlite_file', 'monitoring_se2026.db')
        print(f"Menggunakan SQLite: {db_file}")
        print("Untuk SQLite, tipe data tanggal_tarik tidak perlu diubah secara manual karena SQLite mendukung penyimpanan string DATETIME secara dinamis.")
        print("Skema tabel baru pada penarikan berikutnya otomatis menggunakan DATETIME.")

    elif engine == 'mysql':
        import mysql.connector
        print("Menjalankan migrasi pada MySQL untuk mengubah tipe data tanggal_tarik menjadi DATETIME...")
        try:
            connection = mysql.connector.connect(
                host=db_cfg['host'],
                database=db_cfg['database_name'],
                user=db_cfg['user'],
                password=db_cfg['password']
            )
            cursor = connection.cursor()
            
            # Cek apakah tabel sudah terbentuk
            cursor.execute("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s 
                  AND TABLE_NAME = 'monitoring_se2026'
            """, (db_cfg['database_name'],))
            if cursor.fetchone()[0] == 0:
                print("Tabel 'monitoring_se2026' belum terbentuk. Migrasi dilewati (tabel baru otomatis akan bertipe DATETIME saat script utama jalan).")
                return
                
            # Cek tipe data kolom saat ini
            check_query = """
                SELECT DATA_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                  AND TABLE_NAME = 'monitoring_se2026' 
                  AND COLUMN_NAME = 'tanggal_tarik'
            """
            cursor.execute(check_query, (db_cfg['database_name'],))
            result = cursor.fetchone()
            
            if result and result[0].lower() == 'datetime':
                print("Kolom 'tanggal_tarik' sudah bertipe DATETIME. Migrasi dilewati. ✓")
            else:
                # Modifikasi tipe kolom tanpa merusak data lawas
                cursor.execute("ALTER TABLE monitoring_se2026 MODIFY COLUMN tanggal_tarik DATETIME")
                connection.commit()
                print("Berhasil mengubah tipe kolom 'tanggal_tarik' menjadi DATETIME di tabel 'monitoring_se2026'. ✓")
        except mysql.connector.Error as e:
            print(f"Error MySQL: {e}")
        finally:
            if 'connection' in locals():
                connection.close()
    else:
        print("Engine database tidak dikenali di config.json")

if __name__ == "__main__":
    run_migration()
