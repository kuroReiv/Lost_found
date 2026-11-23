"""Class Database: satu-satunya tempat yang berbicara langsung dengan MySQL."""
from contextlib import contextmanager

import mysql.connector

from config import Config


class Database:
    """Mengelola koneksi MySQL.

    ENCAPSULATION: konfigurasi & koneksi disimpan sebagai atribut private
    (diawali __) sehingga tidak bisa diubah sembarangan dari luar class.
    Class lain cukup memakai method publik: fetch_all, fetch_one, execute, transaction.
    """

    def __init__(self):
        self.__config = {
            "host": Config.DB_HOST,
            "port": Config.DB_PORT,
            "user": Config.DB_USER,
            "password": Config.DB_PASSWORD,
            "database": Config.DB_NAME,
            "charset": "utf8mb4",
            "autocommit": True,        # transaksi dimulai manual lewat transaction()
            "connection_timeout": 5,
        }
        self.__connection = None
        self.__rowcount = 0

    # ---------- koneksi ----------
    def connect(self):
        """Membuat koneksi baru bila belum ada / sudah terputus."""
        if self.__connection is None or not self.__connection.is_connected():
            self.__connection = mysql.connector.connect(**self.__config)
        return self.__connection

    def close(self):
        if self.__connection is not None:
            try:
                self.__connection.close()
            finally:
                self.__connection = None

    @classmethod
    def test_connection(cls):
        """Dipakai check_db.py untuk memastikan MySQL bisa diakses."""
        db = cls()
        try:
            db.connect()
            return True
        finally:
            db.close()

    # ---------- query ----------
    # Semua query memakai parameter (%s) -> mencegah SQL Injection.
    def fetch_all(self, query, params=None):
        cursor = self.connect().cursor(dictionary=True, buffered=True)  # buffered: aman walau sisa baris tidak dibaca
        try:
            cursor.execute(query, params or ())
            return cursor.fetchall()
        finally:
            cursor.close()

    def fetch_one(self, query, params=None):
        cursor = self.connect().cursor(dictionary=True, buffered=True)  # buffered: aman walau sisa baris tidak dibaca
        try:
            cursor.execute(query, params or ())
            return cursor.fetchone()
        finally:
            cursor.close()

    def execute(self, query, params=None):
        """INSERT/UPDATE/DELETE. Mengembalikan id baris terakhir (untuk INSERT)."""
        cursor = self.connect().cursor(buffered=True)
        try:
            cursor.execute(query, params or ())
            self.__rowcount = cursor.rowcount
            return cursor.lastrowid
        finally:
            cursor.close()

    @property
    def rowcount(self):
        """Jumlah baris yang terpengaruh oleh execute() terakhir."""
        return self.__rowcount

    # ---------- transaksi ----------
    @contextmanager
    def transaction(self):
        """Semua query di dalam blok `with` berhasil bersama, atau dibatalkan bersama.

            with db.transaction():
                db.execute(...)
                db.execute(...)
        """
        conn = self.connect()
        conn.start_transaction()
        try:
            yield self
            conn.commit()
        except Exception:
            conn.rollback()
            raise
