# Lost & Found System

Rancang Bangun Aplikasi Lost & Found Berbasis Web Menggunakan Python dengan Penerapan Object Oriented Programming dan Database MySQL.

Stack: Python 3.10+, Flask, MySQL (`mysql-connector-python`), Bootstrap 5. Database yang dipakai: `lost_found_db` (sudah ada, **tidak diubah strukturnya**).

## 1. Struktur file

```
LostFoundSystem/
├── app.py              # merakit aplikasi (blueprint, error handler, CSRF)
├── config.py           # konfigurasi (dibaca dari .env)
├── database.py         # class Database
├── utils.py            # koneksi per-request, CSRF, upload foto
├── check_db.py         # cek koneksi & struktur tabel (hanya membaca)
├── create_admin.py     # membuat akun admin dengan aman
├── requirements.txt, .env.example, .gitignore
├── models/             # user, admin, item, lost_item, found_item, report, claim
├── routes/             # auth, student, admin
├── templates/          # base, login, register, profile, error, _macros, student/, admin/
└── static/             # css/style.css, js/main.js, uploads/
```

## 2. Instalasi library

Buka folder proyek di VS Code, lalu di terminal:

```bash
python -m venv venv
venv\Scripts\activate          # Windows   (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

## 3. Mengatur koneksi MySQL

1. Pastikan MySQL berjalan dan database `lost_found_db` sudah ada.
2. Salin `.env.example` menjadi `.env`, lalu isi:
   ```
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=password_mysql_anda
   DB_NAME=lost_found_db
   SECRET_KEY=teks-acak-yang-panjang
   ```
3. Uji: `python check_db.py`. Skrip ini hanya **membaca**: memeriksa koneksi, tabel, dan kolom.

## 4. Menjalankan aplikasi

```bash
python app.py
```
Buka http://127.0.0.1:5000

## 5. Akun admin

Registrasi publik selalu membuat role `mahasiswa`. Admin dibuat lewat terminal:

```bash
python create_admin.py
```
Skrip meminta nama, email, dan password (diketik tersembunyi), lalu menyimpannya dalam bentuk hash Werkzeug. Tidak ada password yang ditulis di kode. Jika tabel `categories` masih kosong, skrip menawarkan kategori awal. Setelah itu admin dapat mengelola kategori dan pengguna dari dashboard.

## 6. Penerapan OOP

| Konsep | Penerapan |
|---|---|
| **Encapsulation** | `Database` menyimpan konfigurasi & koneksi di atribut private (`__config`, `__connection`). `User` menyimpan hash di `__password_hash` tanpa getter, hanya bisa dipakai lewat `verify_password()`. `Item` memakai `@property` + setter yang memvalidasi nama, deskripsi, dan kategori. |
| **Inheritance** | `Admin` mewarisi `User` (login, profil, ganti password). `LostItem` dan `FoundItem` mewarisi `Item` (kolom, `save`, `update`, `delete`). |
| **Polymorphism** | `Admin` menimpa `get_role_label()` dan `get_dashboard_endpoint()` milik `User`; setelah login, route cukup memanggil `user.get_dashboard_endpoint()`. `LostItem`/`FoundItem` menimpa `get_jenis()`, `get_judul()`, `get_petunjuk()`; form laporan dan kolom `jenis_laporan` ditentukan dari method tersebut. |
| **Abstraction** | `Item` adalah *abstract class* (`ABC`) dengan method abstract `get_jenis`, `get_judul`, `get_petunjuk`. `Item(...)` tidak bisa dibuat langsung. Route cukup memakai `Report.create(...)` tanpa tahu detail SQL. |

Pembagian tanggung jawab: `Database` (koneksi/query/transaksi), `User`/`Admin` (akun & hak admin), `Item` dan turunannya (tabel `items`), `Report` (tabel `reports`), `Claim` (tabel `claims`). Route hanya menerima request, memanggil model, dan merender template.

## 7. Hubungan tabel dengan fitur

| Tabel | Dipakai oleh | Fitur |
|---|---|---|
| `users` | `User`, `Admin` | registrasi, login, profil, kelola pengguna, nama pelapor/pengklaim |
| `categories` | `Item.get_categories`, `Admin` | dropdown & filter kategori, CRUD kategori oleh admin |
| `items` | `Item`, `LostItem`, `FoundItem` | nama, deskripsi, foto, kategori barang |
| `reports` | `Report` | laporan hilang/ditemukan, pencarian, filter, riwayat, status barang, statistik |
| `claims` | `Claim`, `Admin` | ajukan klaim, status klaim, setujui/tolak/selesai, `admin_id` pemverifikasi |

Relasi: `reports.user_id → users`, `reports.item_id → items`, `items.category_id → categories`, `claims.report_id → reports`, `claims.claimant_id → users`, `claims.admin_id → users`.

## Aturan sistem dan lokasinya

- Hanya laporan `ditemukan` + `aktif` yang bisa diklaim, tidak boleh milik sendiri, tidak boleh klaim ganda yang masih `menunggu`: `Claim.create()`.
- Klaim disetujui → laporan `diklaim`, `admin_id` tercatat, klaim lain yang menunggu untuk laporan yang sama otomatis `ditolak`: `Claim.approve()` (satu transaksi). Setelah barang diserahkan, admin menekan "Tandai diserahkan" → klaim `selesai`, laporan `dikembalikan`.
- Mahasiswa hanya bisa mengubah/menghapus laporannya sendiri selama `aktif` dan belum ada klaim: `Report.can_modify()`.
- Blueprint `/admin` menolak non-admin (403); blueprint `/mahasiswa` menolak admin.
- Password di-hash Werkzeug; semua query memakai parameter `%s`; proteksi CSRF pada semua POST; upload foto divalidasi ekstensi **dan** isi file (JPG/PNG/WEBP, maks 2 MB) dan disimpan dengan nama acak.
- Transaksi (`with db.transaction()`): membuat/mengubah/menghapus laporan (items + reports), setuju/tolak/selesai klaim, ubah status laporan oleh admin.
- Nilai `status` pada `claims` yang dipakai: `menunggu`, `disetujui`, `ditolak`, `selesai`.

## Catatan

- Struktur database **tidak diubah**. Tabel tidak memakai `created_at`, jadi urutan laporan memakai `report_id` terbesar.
- Tabel `claims` tidak punya constraint unik, jadi pencegahan klaim ganda dilakukan di kode (`Claim.create`).
- Laporan yang sudah punya klaim tidak bisa dihapus pemiliknya (menjaga relasi FK). Pengguna yang punya laporan/klaim tidak bisa dihapus admin.
- Bootstrap dan ikon dimuat dari CDN, jadi perlu internet saat membuka halaman.
