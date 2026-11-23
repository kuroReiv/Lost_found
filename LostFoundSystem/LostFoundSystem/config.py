"""Konfigurasi aplikasi. Nilai dibaca dari file .env (jika ada) atau environment."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()  # membaca file .env di folder proyek
except ImportError:  # python-dotenv bersifat opsional
    pass

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "ganti-kunci-ini-di-file-env")

    # --- Koneksi MySQL ---
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "lost_found_db")  # database yang SUDAH ada

    # --- Upload foto ---
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # maksimal 2 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
