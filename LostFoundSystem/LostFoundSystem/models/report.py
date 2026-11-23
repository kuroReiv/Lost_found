"""Class Report: laporan barang hilang / ditemukan. Tabel: reports (+ items)."""
from datetime import date, datetime

from models.found_item import FoundItem
from models.lost_item import LostItem

# POLYMORPHISM: jenis laporan -> class yang sesuai
ITEM_CLASSES = {"hilang": LostItem, "ditemukan": FoundItem}

# Query dasar: laporan + barang + kategori + nama pelapor (tanpa password!)
BASE_SELECT = """
    SELECT r.report_id, r.user_id, r.item_id, r.jenis_laporan, r.lokasi,
           r.tanggal_kejadian, r.status,
           i.nama_barang, i.deskripsi, i.foto, i.category_id,
           c.nama_kategori, u.nama AS nama_pelapor
    FROM reports r
    JOIN items i ON i.item_id = r.item_id
    LEFT JOIN categories c ON c.category_id = i.category_id
    JOIN users u ON u.user_id = r.user_id
"""


def buat_item(jenis, db, **data):
    """Membuat LostItem atau FoundItem sesuai jenis laporan."""
    if jenis not in ITEM_CLASSES:
        raise ValueError("Jenis laporan tidak valid.")
    return ITEM_CLASSES[jenis](db, **data)


class Report:
    STATUS_LIST = ("aktif", "diklaim", "dikembalikan", "ditutup")

    def __init__(self, db):
        self._db = db

    # ---------- validasi ----------
    @staticmethod
    def validate_lokasi(lokasi):
        lokasi = (lokasi or "").strip()
        if not 3 <= len(lokasi) <= 150:
            raise ValueError("Lokasi harus 3-150 karakter.")
        return lokasi

    @staticmethod
    def validate_tanggal(teks):
        try:
            tanggal = datetime.strptime((teks or "").strip(), "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Tanggal kejadian tidak valid.")
        if tanggal > date.today():
            raise ValueError("Tanggal kejadian tidak boleh di masa depan.")
        return tanggal

    # ---------- READ ----------
    def search(self, keyword="", category_id=None, jenis="", status="", user_id=None, limit=100):
        """Pencarian + filter. Semua nilai dimasukkan lewat parameter (%s), bukan digabung ke teks SQL."""
        where, params = [], []
        if keyword:
            where.append("i.nama_barang LIKE %s")
            params.append(f"%{keyword}%")
        if category_id:
            where.append("i.category_id = %s")
            params.append(category_id)
        if jenis in ITEM_CLASSES:
            where.append("r.jenis_laporan = %s")
            params.append(jenis)
        if status in self.STATUS_LIST:
            where.append("r.status = %s")
            params.append(status)
        if user_id:
            where.append("r.user_id = %s")
            params.append(user_id)
        sql = BASE_SELECT
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY r.report_id DESC LIMIT %s"
        params.append(limit)
        return self._db.fetch_all(sql, params)

    def get_by_id(self, report_id):
        return self._db.fetch_one(BASE_SELECT + " WHERE r.report_id = %s", (report_id,))

    def count_claims(self, report_id):
        row = self._db.fetch_one("SELECT COUNT(*) AS total FROM claims WHERE report_id = %s", (report_id,))
        return row["total"]

    def can_modify(self, laporan):
        """Laporan hanya boleh diubah/dihapus jika masih 'aktif' dan belum ada klaim."""
        return laporan["status"] == "aktif" and self.count_claims(laporan["report_id"]) == 0

    def summary_by_user(self, user_id):
        row = self._db.fetch_one(
            """SELECT COUNT(*) AS total,
                      COALESCE(SUM(jenis_laporan = 'hilang'), 0) AS hilang,
                      COALESCE(SUM(jenis_laporan = 'ditemukan'), 0) AS ditemukan
               FROM reports WHERE user_id = %s""",
            (user_id,),
        )
        return {k: int(v) for k, v in row.items()}

    # ---------- CREATE ----------
    def create(self, user_id, jenis, category_id, nama_barang, deskripsi, lokasi, tanggal, foto=None):
        """Menyimpan barang + laporan dalam SATU transaksi (keduanya berhasil, atau tidak sama sekali)."""
        item = buat_item(jenis, self._db, foto=foto)
        item.category_id = category_id      # setter memvalidasi
        item.nama_barang = nama_barang
        item.deskripsi = deskripsi
        lokasi = self.validate_lokasi(lokasi)
        tanggal = self.validate_tanggal(tanggal)
        with self._db.transaction():
            item.save()
            return self._db.execute(
                """INSERT INTO reports (user_id, item_id, jenis_laporan, lokasi, tanggal_kejadian, status)
                   VALUES (%s, %s, %s, %s, %s, 'aktif')""",
                (user_id, item.item_id, item.get_jenis(), lokasi, tanggal),
            )

    # ---------- UPDATE ----------
    def update(self, report_id, user_id, category_id, nama_barang, deskripsi, lokasi, tanggal, foto_baru=None):
        """Mengubah laporan milik sendiri. Mengembalikan nama foto lama bila foto diganti (untuk dihapus dari disk)."""
        laporan = self.get_by_id(report_id)
        if laporan is None or laporan["user_id"] != user_id:
            raise ValueError("Laporan tidak ditemukan.")
        if not self.can_modify(laporan):
            raise ValueError("Laporan sudah diproses dan tidak dapat diubah.")

        item = buat_item(
            laporan["jenis_laporan"], self._db, item_id=laporan["item_id"], foto=laporan["foto"]
        )
        item.category_id = category_id
        item.nama_barang = nama_barang
        item.deskripsi = deskripsi
        lokasi = self.validate_lokasi(lokasi)
        tanggal = self.validate_tanggal(tanggal)
        foto_lama = None
        if foto_baru:
            foto_lama = laporan["foto"]
            item.foto = foto_baru
        with self._db.transaction():
            item.update()
            self._db.execute(
                "UPDATE reports SET lokasi = %s, tanggal_kejadian = %s WHERE report_id = %s",
                (lokasi, tanggal, report_id),
            )
        return foto_lama

    # ---------- DELETE ----------
    def delete(self, report_id, user_id):
        """Menghapus laporan + barangnya (satu transaksi). Mengembalikan nama foto untuk dihapus dari disk."""
        laporan = self.get_by_id(report_id)
        if laporan is None or laporan["user_id"] != user_id:
            raise ValueError("Laporan tidak ditemukan.")
        if not self.can_modify(laporan):
            raise ValueError("Laporan sudah diproses dan tidak dapat dihapus.")
        item = buat_item(laporan["jenis_laporan"], self._db, item_id=laporan["item_id"])
        with self._db.transaction():
            self._db.execute("DELETE FROM reports WHERE report_id = %s", (report_id,))
            item.delete()
        return laporan["foto"]
