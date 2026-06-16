import csv
import json
import os
import mysql.connector

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def get_db_connection(config):
    db_cfg = config['database']
    return mysql.connector.connect(
        host=db_cfg['host'],
        user=db_cfg['user'],
        password=db_cfg['password'],
        database=db_cfg['database_name']
    )

def import_csv(file_path):
    config = load_config()
    connection = get_db_connection(config)
    
    petugas_data = {}
    
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header1 = next(reader) # first row usually has some random headers in google sheets export
        header2 = next(reader) # actual headers
        
        # Cari index kolom
        try:
            idx_nama_ppl = header2.index('Nama PPL')
            idx_email_ppl = header2.index('Email PPL')
            idx_nama_pml = header2.index('Nama PML')
            idx_email_pml = header2.index('Email PML')
        except ValueError as e:
            print(f"Error parsing headers: {e}")
            return
            
        for row in reader:
            if len(row) > idx_email_pml:
                nama_ppl = row[idx_nama_ppl].strip()
                email_ppl = row[idx_email_ppl].strip()
                nama_pml = row[idx_nama_pml].strip()
                email_pml = row[idx_email_pml].strip()
                
                if email_ppl and email_ppl != "" and email_ppl != "-":
                    petugas_data[email_ppl] = {"nama": nama_ppl, "peran": "Pencacah"}
                if email_pml and email_pml != "" and email_pml != "-":
                    petugas_data[email_pml] = {"nama": nama_pml, "peran": "Pengawas"}

    print(f"Ditemukan {len(petugas_data)} petugas unik.")
    
    try:
        with connection.cursor() as cursor:
            count_inserted = 0
            for email, info in petugas_data.items():
                sql = """
                INSERT INTO master_petugas (email, nama_lengkap, peran)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                nama_lengkap = VALUES(nama_lengkap),
                peran = VALUES(peran)
                """
                cursor.execute(sql, (email, info['nama'], info['peran']))
                count_inserted += 1
                
            connection.commit()
            print(f"Berhasil menyimpan {count_inserted} data ke tabel master_petugas.")
    except Exception as e:
        print(f"Error Database: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    if os.path.exists('master_petugas.csv'):
        print("Mengimpor data dari master_petugas.csv...")
        import_csv('master_petugas.csv')
    else:
        print("File master_petugas.csv tidak ditemukan.")
