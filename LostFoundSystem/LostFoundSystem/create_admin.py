"""Membuat akun admin dengan aman (password diketik tersembunyi lalu di-hash).

Jalankan:  python create_admin.py
Tidak ada password yang tertulis di kode maupun di database dalam bentuk asli.
"""
from getpass import getpass

from werkzeug.security import generate_password_hash

from database import Database
from models.user import User

KATEGORI_AWAL = ["Dompet & Tas", "Elektronik", "Dokumen & Kartu", "Kunci", "Pakaian & Aksesoris", "Alat Tulis & Buku", "Lainnya"]


def main():
    db = Database()
    try:
        print("=== Buat akun admin Lost & Found ===")
        nama = User.validate_nama(input("Nama lengkap : "))
        email = User.validate_email(input("Email        : "))
        password = User.validate_password(getpass("Password     : "))
        if password != getpass("Ulangi       : "):
            print("Password tidak sama. Dibatalkan.")
            return 1

        ada = db.fetch_one("SELECT user_id, role FROM users WHERE email = %s", (email,))
        if ada:
            if ada["role"] == "admin":
                print("Email tersebut sudah menjadi admin.")
                return 1
            if input("Email sudah terdaftar sebagai mahasiswa. Jadikan admin? (y/n): ").lower() != "y":
                return 1
            db.execute("UPDATE users SET role = 'admin' WHERE user_id = %s", (ada["user_id"],))
            print("Akun diubah menjadi admin (password lama tetap berlaku).")
        else:
            db.execute(
                "INSERT INTO users (nama, email, password, role) VALUES (%s, %s, %s, 'admin')",
                (nama, email, generate_password_hash(password)),
            )
            print("Akun admin berhasil dibuat.")

        # Kategori awal hanya ditambahkan bila tabel categories masih kosong (tidak menimpa data).
        if db.fetch_one("SELECT COUNT(*) AS n FROM categories")["n"] == 0:
            if input("Tabel kategori masih kosong. Tambahkan kategori awal? (y/n): ").lower() == "y":
                for k in KATEGORI_AWAL:
                    db.execute("INSERT INTO categories (nama_kategori) VALUES (%s)", (k,))
                print(f"{len(KATEGORI_AWAL)} kategori ditambahkan.")
        return 0
    except ValueError as e:
        print(f"Input tidak valid: {e}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
