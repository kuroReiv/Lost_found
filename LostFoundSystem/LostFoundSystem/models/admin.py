"""Class Admin (turunan User): mengelola laporan, klaim, kategori, dan pengguna."""
from models.claim import Claim
from models.report import Report
from models.user import User


class Admin(User):
    """INHERITANCE: Admin otomatis punya login, profil, dan password dari User.
    POLYMORPHISM: dua method di bawah menimpa (override) milik User."""

    def __init__(self, db, user_id=None, nama="", email="", password_hash=""):
        super().__init__(db, user_id, nama, email, password_hash, role="admin")

    # ---------- override ----------
    def get_role_label(self):
        return "Administrator"

    def get_dashboard_endpoint(self):
        return "admin.dashboard"

    # ---------- statistik ----------
    def get_statistics(self):
        laporan = self._db.fetch_one(
            """SELECT COUNT(*) AS total,
                      COALESCE(SUM(jenis_laporan = 'hilang'), 0) AS hilang,
                      COALESCE(SUM(jenis_laporan = 'ditemukan'), 0) AS ditemukan,
                      COALESCE(SUM(status = 'diklaim'), 0) AS diklaim,
                      COALESCE(SUM(status = 'dikembalikan'), 0) AS dikembalikan
               FROM reports"""
        )
        stat = {k: int(v) for k, v in laporan.items()}
        stat["klaim_menunggu"] = self._db.fetch_one(
            "SELECT COUNT(*) AS n FROM claims WHERE status = 'menunggu'")["n"]
        stat["pengguna"] = self._db.fetch_one("SELECT COUNT(*) AS n FROM users")["n"]
        return stat

    # ---------- laporan ----------
    def update_report_status(self, report_id, status):
        """Ubah status laporan. Semua perubahan terkait berjalan dalam satu transaksi."""
        if status not in Report.STATUS_LIST:
            raise ValueError("Status tidak valid.")
        with self._db.transaction():
            laporan = self._db.fetch_one(
                "SELECT status FROM reports WHERE report_id = %s FOR UPDATE", (report_id,))
            if laporan is None:
                raise ValueError("Laporan tidak ditemukan.")
            if status == "aktif" and self._db.fetch_one(
                "SELECT claim_id FROM claims WHERE report_id = %s AND status IN ('disetujui','selesai')", (report_id,)
            ):
                raise ValueError("Sudah ada klaim yang disetujui, status tidak dapat dikembalikan ke aktif.")
            self._db.execute("UPDATE reports SET status = %s WHERE report_id = %s", (status, report_id))
            if status != "aktif":  # klaim yang masih menunggu tidak relevan lagi
                self._db.execute(
                    "UPDATE claims SET status = 'ditolak', admin_id = %s WHERE report_id = %s AND status = 'menunggu'",
                    (self.user_id, report_id),
                )

    # ---------- klaim (admin_id tercatat otomatis) ----------
    def approve_claim(self, claim_id):
        Claim(self._db).approve(claim_id, self.user_id)

    def reject_claim(self, claim_id):
        Claim(self._db).reject(claim_id, self.user_id)

    def complete_claim(self, claim_id):
        Claim(self._db).complete(claim_id, self.user_id)

    # ---------- kategori ----------
    @staticmethod
    def _validate_kategori(nama):
        nama = (nama or "").strip()
        if not 2 <= len(nama) <= 100:
            raise ValueError("Nama kategori harus 2-100 karakter.")
        return nama

    def get_categories_with_count(self):
        return self._db.fetch_all(
            """SELECT c.category_id, c.nama_kategori, COUNT(i.item_id) AS jumlah_barang
               FROM categories c LEFT JOIN items i ON i.category_id = c.category_id
               GROUP BY c.category_id, c.nama_kategori ORDER BY c.nama_kategori"""
        )

    def add_category(self, nama):
        nama = self._validate_kategori(nama)
        if self._db.fetch_one("SELECT category_id FROM categories WHERE LOWER(nama_kategori) = LOWER(%s)", (nama,)):
            raise ValueError("Kategori tersebut sudah ada.")
        return self._db.execute("INSERT INTO categories (nama_kategori) VALUES (%s)", (nama,))

    def update_category(self, category_id, nama):
        nama = self._validate_kategori(nama)
        if self._db.fetch_one(
            "SELECT category_id FROM categories WHERE LOWER(nama_kategori) = LOWER(%s) AND category_id <> %s", (nama, category_id)
        ):
            raise ValueError("Kategori tersebut sudah ada.")
        self._db.execute("UPDATE categories SET nama_kategori = %s WHERE category_id = %s", (nama, category_id))

    def delete_category(self, category_id):
        pakai = self._db.fetch_one("SELECT COUNT(*) AS n FROM items WHERE category_id = %s", (category_id,))["n"]
        if pakai:
            raise ValueError(f"Kategori masih dipakai {pakai} barang, tidak dapat dihapus.")
        self._db.execute("DELETE FROM categories WHERE category_id = %s", (category_id,))

    # ---------- pengguna (password tidak pernah diambil) ----------
    def list_users(self):
        return self._db.fetch_all(
            """SELECT u.user_id, u.nama, u.email, u.role,
                      (SELECT COUNT(*) FROM reports r WHERE r.user_id = u.user_id) AS jumlah_laporan
               FROM users u ORDER BY u.user_id"""
        )

    def change_user_role(self, target_id, role):
        if role not in ("mahasiswa", "admin"):
            raise ValueError("Role tidak valid.")
        if target_id == self.user_id:
            raise ValueError("Anda tidak dapat mengubah role akun sendiri.")
        self._db.execute("UPDATE users SET role = %s WHERE user_id = %s", (role, target_id))
        if self._db.rowcount == 0 and not self._db.fetch_one("SELECT user_id FROM users WHERE user_id = %s", (target_id,)):
            raise ValueError("Pengguna tidak ditemukan.")

    def delete_user(self, target_id):
        if target_id == self.user_id:
            raise ValueError("Anda tidak dapat menghapus akun sendiri.")
        terkait = self._db.fetch_one(
            """SELECT (SELECT COUNT(*) FROM reports WHERE user_id = %s)
                    + (SELECT COUNT(*) FROM claims WHERE claimant_id = %s OR admin_id = %s) AS n""",
            (target_id, target_id, target_id),
        )["n"]
        if terkait:
            raise ValueError("Pengguna memiliki laporan/klaim sehingga tidak dapat dihapus.")
        self._db.execute("DELETE FROM users WHERE user_id = %s", (target_id,))
