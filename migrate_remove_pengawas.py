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
        import sqlite3
        db_file = db_cfg.get('sqlite_file', 'monitoring_se2026.db')
        print(f"Menjalankan migrasi pada SQLite: {db_file}")
        
        try:
            connection = sqlite3.connect(db_file)
            cursor = connection.cursor()
            cursor.execute("ALTER TABLE monitoring_se2026 DROP COLUMN email_pengawas")
            connection.commit()
            print("Berhasil menghapus kolom 'email_pengawas' dari tabel 'monitoring_se2026'.")
        except sqlite3.OperationalError as e:
            # Drop column not supported in older SQLite versions or column doesn't exist
            if "syntax error" in str(e).lower() or "near \"DROP\"" in str(e).lower():
                print("Versi SQLite-mu tidak mendukung perintah DROP COLUMN (butuh versi 3.35.0+).")
                print("Namun jangan khawatir, kamu bisa mengabaikan kolom tersebut.")
            else:
                print(f"Pesan: {e} (Kemungkinan kolom sudah tidak ada)")
        finally:
            if 'connection' in locals():
                connection.close()

    elif engine == 'mysql':
        import mysql.connector
        print("Menjalankan migrasi pada MySQL...")
        try:
            connection = mysql.connector.connect(
                host=db_cfg['host'],
                database=db_cfg['database_name'],
                user=db_cfg['user'],
                password=db_cfg['password']
            )
            cursor = connection.cursor()
            cursor.execute("ALTER TABLE monitoring_se2026 DROP COLUMN email_pengawas")
            connection.commit()
            print("Berhasil menghapus kolom 'email_pengawas' dari tabel 'monitoring_se2026'.")
        except mysql.connector.Error as e:
            print(f"Error MySQL: {e} (Kemungkinan kolom sudah tidak ada)")
        finally:
            if 'connection' in locals():
                connection.close()
    else:
        print("Engine database tidak dikenali di config.json")

if __name__ == "__main__":
    run_migration()
