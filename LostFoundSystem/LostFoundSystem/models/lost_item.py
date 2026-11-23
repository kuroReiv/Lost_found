"""LostItem: barang yang dilaporkan HILANG."""
from models.item import Item


class LostItem(Item):
    """INHERITANCE: mewarisi semua isi Item.
    POLYMORPHISM: tiga method abstract diisi dengan perilaku khusus barang hilang."""

    def get_jenis(self):
        return "hilang"

    def get_judul(self):
        return "Laporkan Barang Hilang"

    def get_petunjuk(self):
        return "Isi lokasi terakhir barang terlihat dan tanggal Anda kehilangan barang."
