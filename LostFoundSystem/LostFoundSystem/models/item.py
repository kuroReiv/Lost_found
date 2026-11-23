"""Class Item: induk (abstract) untuk informasi barang. Tabel: items."""
from abc import ABC, abstractmethod


class Item(ABC):
    """ABSTRACTION: Item tidak boleh dibuat langsung (Item(...) akan error).
    Anak class WAJIB mengisi method abstract get_jenis(), get_judul(), get_petunjuk().

    ENCAPSULATION: data barang disimpan di atribut private dan hanya diubah
    lewat property yang memvalidasi input.
    """

    def __init__(self, db, item_id=None, category_id=None, nama_barang="", deskripsi="", foto=None):
        self._db = db
        self.__item_id = item_id
        self.__category_id = category_id
        self.__nama_barang = nama_barang
        self.__deskripsi = deskripsi
        self.__foto = foto

    # ---------- properties (getter + setter berisi validasi) ----------
    @property
    def item_id(self):
        return self.__item_id

    @property
    def category_id(self):
        return self.__category_id

    @category_id.setter
    def category_id(self, value):
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValueError("Kategori wajib dipilih.")
        if not self._db.fetch_one("SELECT category_id FROM categories WHERE category_id = %s", (value,)):
            raise ValueError("Kategori tidak ditemukan.")
        self.__category_id = value

    @property
    def nama_barang(self):
        return self.__nama_barang

    @nama_barang.setter
    def nama_barang(self, value):
        value = (value or "").strip()
        if not 3 <= len(value) <= 100:
            raise ValueError("Nama barang harus 3-100 karakter.")
        self.__nama_barang = value

    @property
    def deskripsi(self):
        return self.__deskripsi

    @deskripsi.setter
    def deskripsi(self, value):
        value = (value or "").strip()
        if not 10 <= len(value) <= 1000:
            raise ValueError("Deskripsi harus 10-1000 karakter.")
        self.__deskripsi = value

    @property
    def foto(self):
        return self.__foto

    @foto.setter
    def foto(self, value):
        self.__foto = value

    # ---------- method abstract (diisi oleh LostItem / FoundItem) ----------
    @abstractmethod
    def get_jenis(self):
        """Nilai untuk kolom reports.jenis_laporan."""

    @abstractmethod
    def get_judul(self):
        """Judul yang tampil di halaman."""

    @abstractmethod
    def get_petunjuk(self):
        """Teks bantuan pada form laporan."""

    # ---------- operasi database (dipakai bersama oleh semua anak class) ----------
    def save(self):
        """INSERT ke tabel items, lalu menyimpan item_id yang baru dibuat."""
        self.__item_id = self._db.execute(
            "INSERT INTO items (category_id, nama_barang, deskripsi, foto) VALUES (%s, %s, %s, %s)",
            (self.__category_id, self.__nama_barang, self.__deskripsi, self.__foto),
        )
        return self.__item_id

    def update(self):
        self._db.execute(
            "UPDATE items SET category_id = %s, nama_barang = %s, deskripsi = %s, foto = %s WHERE item_id = %s",
            (self.__category_id, self.__nama_barang, self.__deskripsi, self.__foto, self.__item_id),
        )

    def delete(self):
        self._db.execute("DELETE FROM items WHERE item_id = %s", (self.__item_id,))

    @staticmethod
    def get_categories(db):
        return db.fetch_all("SELECT category_id, nama_kategori FROM categories ORDER BY nama_kategori")
