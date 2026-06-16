#!/bin/bash
# ==========================================
echo "=========================================="
echo "   MONITORING PROGRESS LAPANGAN SE2026"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

echo "Menyiapkan browser Chrome khusus (terisolasi)..."
mkdir -p /tmp/chrome-debug
nohup /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome-debug" > /dev/null 2>&1 &

sleep 3
echo "INSTRUKSI PENTING:"
echo "------------------"
echo "Browser Chrome khusus baru saja terbuka secara otomatis."
echo "Silakan login ke FASIH di browser tersebut dan pastikan sampai di Dashboard."
echo "Tekan ENTER di sini JIKA Chrome sudah siap dan sudah login..."
read -r

echo ""
echo "=========================================="
echo "               MENU UTAMA                 "
echo "=========================================="
echo "Pilih tugas yang ingin dijalankan:"
echo "  [1] Tarik Progress Harian Lapangan (Default)"
echo "  [2] Tarik Master Mapping Pengawas"
echo "  [3] Tarik Keduanya (Pengawas lalu Progress)"
echo "=========================================="
echo -n "Pilih nomor (1/2/3) [Tekan ENTER untuk 1]: "
read -r pilihan

if [ -z "$pilihan" ]; then
    pilihan="1"
fi

echo ""

if [ "$pilihan" = "2" ]; then
    echo "▶ Menjalankan Penarikan Master Pengawas..."
    python3 fetch_pengawas.py
elif [ "$pilihan" = "3" ]; then
    echo "▶ Menjalankan Penarikan Master Pengawas..."
    python3 fetch_pengawas.py
    echo ""
    echo "▶ Menjalankan Penarikan Progress Harian..."
    python3 monitoring_lapangan.py
else
    echo "▶ Menjalankan Penarikan Progress Harian..."
    python3 monitoring_lapangan.py
fi

echo ""
echo "Script selesai."
