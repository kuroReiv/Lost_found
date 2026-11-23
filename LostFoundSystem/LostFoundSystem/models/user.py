"""Class User: registrasi, login, dan profil. Tabel: users."""
import re

from mysql.connector import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class User:
    """Pengguna biasa (mahasiswa).

    ENCAPSULATION: hash password disimpan di atribut private __password_hash.
    Tidak ada getter-nya; satu-satunya cara memakainya adalah verify_password().
    """

    def __init__(self, db, user_id=None, nama="", email="", password_hash="", role="mahasiswa"):
        self._db = db
        self._user_id = user_id
        self._nama = nama
        self._email = email
        self.__password_hash = password_hash
        self._role = role

    # ---------- properties ----------
    @property
    def user_id(self):
        return self._user_id

    @property
    def nama(self):
        return self._nama

    @nama.setter
    def nama(self, value):
        self._nama = self.validate_nama(value)

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, value):
        self._email = self.validate_email(value)

    @property
    def role(self):
        return self._role

    # ---------- validasi (static: tidak butuh objek) ----------
    @staticmethod
    def validate_nama(nama):
        nama = (nama or "").strip()
        if not 3 <= len(nama) <= 100:
            raise ValueError("Nama harus 3-100 karakter.")
        return nama

    @staticmethod
    def validate_email(email):
        email = (email or "").strip().lower()
        if len(email) > 100 or not EMAIL_PATTERN.match(email):
            raise ValueError("Format email tidak valid.")
        return email

    @staticmethod
    def validate_password(password):
        if not password or not 6 <= len(password) <= 100:
            raise ValueError("Password harus 6-100 karakter.")
        return password

    # ---------- POLYMORPHISM: Admin akan menimpa dua method ini ----------
    def get_role_label(self):
        return "Mahasiswa"

    def get_dashboard_endpoint(self):
        return "student.dashboard"

    # ---------- password ----------
    def verify_password(self, password):
        return check_password_hash(self.__password_hash, password or "")

    def change_password(self, lama, baru, konfirmasi):
        if not self.verify_password(lama):
            raise ValueError("Password lama salah.")
        self.validate_password(baru)
        if baru != konfirmasi:
            raise ValueError("Konfirmasi password tidak sama.")
        hashed = generate_password_hash(baru)  # hashing Werkzeug
        self._db.execute("UPDATE users SET password = %s WHERE user_id = %s", (hashed, self._user_id))
        self.__password_hash = hashed

    # ---------- profil ----------
    def update_profile(self, nama, email):
        nama = self.validate_nama(nama)
        email = self.validate_email(email)
        if self._db.fetch_one(
            "SELECT user_id FROM users WHERE email = %s AND user_id <> %s", (email, self._user_id)
        ):
            raise ValueError("Email sudah dipakai pengguna lain.")
        self._db.execute(
            "UPDATE users SET nama = %s, email = %s WHERE user_id = %s", (nama, email, self._user_id)
        )
        self._nama, self._email = nama, email

    # ---------- operasi level class ----------
    @classmethod
    def register(cls, db, nama, email, password, konfirmasi):
        """Mendaftarkan akun baru. Role SELALU 'mahasiswa' (admin dibuat lewat create_admin.py)."""
        nama = cls.validate_nama(nama)
        email = cls.validate_email(email)
        cls.validate_password(password)
        if password != konfirmasi:
            raise ValueError("Konfirmasi password tidak sama.")
        if db.fetch_one("SELECT user_id FROM users WHERE email = %s", (email,)):
            raise ValueError("Email sudah terdaftar.")
        try:
            return db.execute(
                "INSERT INTO users (nama, email, password, role) VALUES (%s, %s, %s, 'mahasiswa')",
                (nama, email, generate_password_hash(password)),
            )
        except IntegrityError:
            raise ValueError("Email sudah terdaftar.")

    @classmethod
    def login(cls, db, email, password):
        """Mengembalikan objek User/Admin bila email & password benar, jika tidak None."""
        row = db.fetch_one("SELECT * FROM users WHERE email = %s", ((email or "").strip().lower(),))
        if row is None:
            return None
        user = cls.from_row(db, row)
        return user if user.verify_password(password) else None

    @classmethod
    def get_by_id(cls, db, user_id):
        row = db.fetch_one("SELECT * FROM users WHERE user_id = %s", (user_id,))
        return cls.from_row(db, row) if row else None

    @staticmethod
    def from_row(db, row):
        """Pabrik objek: role 'admin' -> Admin, selain itu -> User."""
        if row["role"] == "admin":
            from models.admin import Admin  # import di sini agar tidak saling mengunci (circular)
            return Admin(db, row["user_id"], row["nama"], row["email"], row["password"])
        return User(db, row["user_id"], row["nama"], row["email"], row["password"], row["role"])
