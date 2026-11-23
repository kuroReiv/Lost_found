"""Memeriksa koneksi MySQL dan kecocokan struktur tabel. SKRIP INI HANYA MEMBACA, tidak mengubah apa pun.

Jalankan:  python check_db.py
"""
from config import Config
from database import Database

EXPECTED = {
    "users": ["user_id", "nama", "email", "password", "role"],
    "categories": ["category_id", "nama_kategori"],
    "items": ["item_id", "category_id", "nama_barang", "deskripsi", "foto"],
    "reports": ["report_id", "user_id", "item_id", "jenis_laporan", "lokasi", "tanggal_kejadian", "status"],
    "claims": ["claim_id", "report_id", "claimant_id", "admin_id", "alasan_klaim", "status"],
}


def main():
    print(f"Menghubungi MySQL {Config.DB_HOST}:{Config.DB_PORT} database '{Config.DB_NAME}' ...")
    db = Database()
    try:
        db.connect()
    except Exception as e:
        print(f"[GAGAL] Tidak dapat terhubung: {e}")
        print("Periksa file .env (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME) dan pastikan MySQL berjalan.")
        return 1
    print("[OK] Koneksi berhasil.\n")

    masalah = 0
    for tabel, kolom_wajib in EXPECTED.items():
        rows = db.fetch_all(
            "SELECT COLUMN_NAME AS kolom FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s", (Config.DB_NAME, tabel))
        ada = {r["kolom"] for r in rows}
        if not ada:
            print(f"[GAGAL] Tabel '{tabel}' tidak ditemukan.")
            masalah += 1
            continue
        kurang = [k for k in kolom_wajib if k not in ada]
        if kurang:
            print(f"[GAGAL] Tabel '{tabel}' kekurangan kolom: {', '.join(kurang)}")
            masalah += 1
        else:
            jumlah = db.fetch_one(f"SELECT COUNT(*) AS n FROM `{tabel}`")["n"]
            print(f"[OK] {tabel:<11} kolom lengkap, {jumlah} baris")

    if masalah == 0:
        admin = db.fetch_one("SELECT COUNT(*) AS n FROM users WHERE role = 'admin'")["n"]
        kat = db.fetch_one("SELECT COUNT(*) AS n FROM categories")["n"]
        print()
        if admin == 0:
            print("[INFO] Belum ada akun admin. Jalankan: python create_admin.py")
        if kat == 0:
            print("[INFO] Belum ada kategori. create_admin.py dapat menambahkan kategori awal, "
                  "atau tambahkan lewat menu Kategori di dashboard admin.")
    db.close()
    return 1 if masalah else 0


if __name__ == "__main__":
    raise SystemExit(main())
