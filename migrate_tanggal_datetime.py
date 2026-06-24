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
            
            # Kita tidak men-drop atau men-truncate data sesuai aturan. Kita hanya mengubah tipe kolom.
            # Data DATE yang lama (misal: 2026-06-24) otomatis akan menjadi 2026-06-24 00:00:00 di MySQL, sehingga aman.
            cursor.execute("ALTER TABLE monitoring_se2026 MODIFY COLUMN tanggal_tarik DATETIME")
            connection.commit()
            print("Berhasil mengubah tipe kolom 'tanggal_tarik' menjadi DATETIME di tabel 'monitoring_se2026'.")
        except mysql.connector.Error as e:
            print(f"Error MySQL: {e}")
        finally:
            if 'connection' in locals():
                connection.close()
    else:
        print("Engine database tidak dikenali di config.json")

if __name__ == "__main__":
    run_migration()
