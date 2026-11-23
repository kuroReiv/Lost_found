"""FoundItem: barang yang DITEMUKAN."""
from models.item import Item


class FoundItem(Item):
    """INHERITANCE + POLYMORPHISM: method yang sama dengan LostItem, hasilnya berbeda."""

    def get_jenis(self):
        return "ditemukan"

    def get_judul(self):
        return "Laporkan Barang Ditemukan"

    def get_petunjuk(self):
        return ("Isi lokasi barang ditemukan dan tanggal penemuan. "
                "Jangan tulis ciri rahasia barang, agar pemilik asli bisa membuktikannya saat klaim.")
