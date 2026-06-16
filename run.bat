@echo off
title Monitoring Lapangan SE2026
echo ==========================================
echo    MONITORING PROGRESS LAPANGAN SE2026
echo ==========================================
echo.

cd /d "%~dp0"

echo INSTRUKSI PENTING SEBELUM MULAI:
echo --------------------------------
echo Pastikan kamu sudah membuka Chrome khusus dengan mode debugging!
echo Jika Chrome gagal tersambung, matikan Chrome di Task Manager lalu buka CMD:
echo "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
echo.
echo Setelah Chrome terbuka, login ke FASIH dan pastikan sampai di Dashboard.
echo Tekan ENTER di bawah ini jika Chrome sudah siap dan login...
pause

echo.
echo ==========================================
echo                MENU UTAMA                 
echo ==========================================
echo Pilih tugas yang ingin dijalankan:
echo   [1] Tarik Progress Harian Lapangan (Default)
echo   [2] Tarik Master Mapping Pengawas
echo   [3] Tarik Keduanya (Pengawas lalu Progress)
echo ==========================================
set /p pilihan="Pilih nomor (1/2/3) [Tekan ENTER untuk 1]: "

if "%pilihan%"=="" set pilihan=1

echo.

if "%pilihan%"=="2" (
    echo ▶ Menjalankan Penarikan Master Pengawas...
    python fetch_pengawas.py
) else if "%pilihan%"=="3" (
    echo ▶ Menjalankan Penarikan Master Pengawas...
    python fetch_pengawas.py
    echo.
    echo ▶ Menjalankan Penarikan Progress Harian...
    python monitoring_lapangan.py
) else (
    echo ▶ Menjalankan Penarikan Progress Harian...
    python monitoring_lapangan.py
)

echo.
pause
