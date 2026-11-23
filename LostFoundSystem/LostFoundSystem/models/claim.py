"""Class Claim: pengajuan klaim dan perubahan statusnya. Tabel: claims (+ reports)."""

BASE_SELECT = """
    SELECT c.claim_id, c.report_id, c.claimant_id, c.admin_id, c.alasan_klaim,
           c.status AS status_klaim,
           r.status AS status_laporan, r.lokasi, r.tanggal_kejadian, r.user_id AS pelapor_id,
           i.nama_barang, i.foto,
           u.nama AS nama_pengklaim, u.email AS email_pengklaim,
           a.nama AS nama_admin
    FROM claims c
    JOIN reports r ON r.report_id = c.report_id
    JOIN items i ON i.item_id = r.item_id
    JOIN users u ON u.user_id = c.claimant_id
    LEFT JOIN users a ON a.user_id = c.admin_id
"""


class Claim:
    STATUS_LIST = ("menunggu", "disetujui", "ditolak", "selesai")

    def __init__(self, db):
        self._db = db

    # ---------- READ ----------
    def get_by_claimant(self, user_id):
        return self._db.fetch_all(BASE_SELECT + " WHERE c.claimant_id = %s ORDER BY c.claim_id DESC", (user_id,))

    def get_by_report_and_claimant(self, report_id, user_id):
        return self._db.fetch_all(
            BASE_SELECT + " WHERE c.report_id = %s AND c.claimant_id = %s ORDER BY c.claim_id DESC",
            (report_id, user_id),
        )

    def get_by_report(self, report_id):
        return self._db.fetch_all(BASE_SELECT + " WHERE c.report_id = %s ORDER BY c.claim_id DESC", (report_id,))

    def get_all(self, status=""):
        if status in self.STATUS_LIST:
            return self._db.fetch_all(BASE_SELECT + " WHERE c.status = %s ORDER BY c.claim_id DESC", (status,))
        return self._db.fetch_all(BASE_SELECT + " ORDER BY c.claim_id DESC")

    def has_pending(self, report_id, user_id):
        row = self._db.fetch_one(
            "SELECT claim_id FROM claims WHERE report_id = %s AND claimant_id = %s AND status = 'menunggu'",
            (report_id, user_id),
        )
        return row is not None

    def count_by_claimant(self, user_id):
        rows = self._db.fetch_all(
            "SELECT status, COUNT(*) AS total FROM claims WHERE claimant_id = %s GROUP BY status", (user_id,)
        )
        hasil = {s: 0 for s in self.STATUS_LIST}
        for r in rows:
            hasil[r["status"]] = r["total"]
        return hasil

    # ---------- CREATE ----------
    def create(self, report_id, claimant_id, alasan):
        """Mengajukan klaim. Aturan sistem dicek di sini, bukan hanya di tampilan."""
        alasan = (alasan or "").strip()
        if not 10 <= len(alasan) <= 1000:
            raise ValueError("Alasan klaim harus 10-1000 karakter (jelaskan ciri barang untuk bukti).")
        with self._db.transaction():
            # FOR UPDATE mengunci baris laporan agar dua klaim tidak bentrok
            laporan = self._db.fetch_one(
                "SELECT report_id, user_id, jenis_laporan, status FROM reports WHERE report_id = %s FOR UPDATE",
                (report_id,),
            )
            if laporan is None:
                raise ValueError("Laporan tidak ditemukan.")
            if laporan["jenis_laporan"] != "ditemukan":
                raise ValueError("Hanya laporan barang ditemukan yang dapat diklaim.")
            if laporan["status"] != "aktif":
                raise ValueError("Laporan ini tidak lagi aktif.")
            if laporan["user_id"] == claimant_id:
                raise ValueError("Anda tidak dapat mengklaim laporan milik sendiri.")
            if self.has_pending(report_id, claimant_id):
                raise ValueError("Anda sudah mengajukan klaim yang masih menunggu untuk laporan ini.")
            return self._db.execute(
                "INSERT INTO claims (report_id, claimant_id, admin_id, alasan_klaim, status) "
                "VALUES (%s, %s, NULL, %s, 'menunggu')",
                (report_id, claimant_id, alasan),
            )

    # ---------- perubahan status (dipanggil oleh Admin) ----------
    def _lock_claim(self, claim_id, status_harus):
        claim = self._db.fetch_one(
            "SELECT claim_id, report_id, status FROM claims WHERE claim_id = %s FOR UPDATE", (claim_id,)
        )
        if claim is None:
            raise ValueError("Klaim tidak ditemukan.")
        if claim["status"] != status_harus:
            raise ValueError(f"Klaim ini berstatus '{claim['status']}', bukan '{status_harus}'.")
        return claim

    def approve(self, claim_id, admin_id):
        """Setujui klaim: klaim -> disetujui, laporan -> diklaim, klaim lain yang menunggu -> ditolak."""
        with self._db.transaction():
            claim = self._lock_claim(claim_id, "menunggu")
            laporan = self._db.fetch_one(
                "SELECT status FROM reports WHERE report_id = %s FOR UPDATE", (claim["report_id"],)
            )
            if laporan is None or laporan["status"] != "aktif":
                raise ValueError("Laporan sudah tidak aktif, klaim tidak dapat disetujui.")
            self._db.execute(
                "UPDATE claims SET status = 'disetujui', admin_id = %s WHERE claim_id = %s", (admin_id, claim_id)
            )
            self._db.execute("UPDATE reports SET status = 'diklaim' WHERE report_id = %s", (claim["report_id"],))
            self._db.execute(
                "UPDATE claims SET status = 'ditolak', admin_id = %s "
                "WHERE report_id = %s AND status = 'menunggu' AND claim_id <> %s",
                (admin_id, claim["report_id"], claim_id),
            )

    def reject(self, claim_id, admin_id):
        with self._db.transaction():
            self._lock_claim(claim_id, "menunggu")
            self._db.execute(
                "UPDATE claims SET status = 'ditolak', admin_id = %s WHERE claim_id = %s", (admin_id, claim_id)
            )

    def complete(self, claim_id, admin_id):
        """Barang sudah diserahkan: klaim -> selesai, laporan -> dikembalikan."""
        with self._db.transaction():
            claim = self._lock_claim(claim_id, "disetujui")
            self._db.execute(
                "UPDATE claims SET status = 'selesai', admin_id = %s WHERE claim_id = %s", (admin_id, claim_id)
            )
            self._db.execute(
                "UPDATE reports SET status = 'dikembalikan' WHERE report_id = %s", (claim["report_id"],)
            )
