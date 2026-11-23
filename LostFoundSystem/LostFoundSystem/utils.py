"""Fungsi bantu: koneksi per-request, hak akses, CSRF, dan upload foto."""
import os
import secrets
import uuid
from functools import wraps

from flask import abort, current_app, flash, g, redirect, request, session, url_for

from database import Database


# ---------- koneksi database per request ----------
def get_db():
    """Satu objek Database per request, disimpan di flask.g."""
    if "db" not in g:
        g.db = Database()
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ---------- hak akses ----------
def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.get("user") is None:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapper


# ---------- CSRF sederhana ----------
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


def csrf_protect():
    """Semua request POST wajib membawa token yang sama dengan session."""
    if request.method == "POST":
        sent = request.form.get("csrf_token", "")
        saved = session.get("_csrf", "")
        if not saved or not secrets.compare_digest(saved, sent):
            abort(400)


# ---------- helper kecil ----------
def to_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------- upload foto ----------
def _signature_ok(header, ext):
    """Cek isi file (bukan hanya nama) agar file palsu tidak lolos."""
    if header.startswith(b"\xff\xd8\xff"):
        return ext in ("jpg", "jpeg")
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ext == "png"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return ext == "webp"
    return False


def save_foto(file):
    """Validasi & simpan foto. Mengembalikan nama file baru, atau None jika tidak ada file."""
    if file is None or not file.filename:
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
        raise ValueError("Format foto harus JPG, PNG, atau WEBP.")
    header = file.stream.read(16)
    file.stream.seek(0)
    if not _signature_ok(header, ext):
        raise ValueError("Isi file bukan gambar yang valid.")
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    nama_file = f"{uuid.uuid4().hex}.{ext}"  # nama acak, bukan nama dari pengguna
    file.save(os.path.join(folder, nama_file))
    return nama_file


def delete_foto(nama_file):
    if not nama_file:
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(nama_file))
    if os.path.isfile(path):
        os.remove(path)
