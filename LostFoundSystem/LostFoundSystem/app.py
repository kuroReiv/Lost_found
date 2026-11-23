"""Titik masuk aplikasi. Hanya merakit komponen; logika ada di models/ dan routes/."""
from datetime import date

import mysql.connector
from flask import Flask, g, render_template, session

from config import Config
from models.user import User
from routes.admin import bp as admin_bp
from routes.auth import bp as auth_bp
from routes.student import bp as student_bp
from utils import close_db, csrf_protect, csrf_token, get_db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)

    app.teardown_appcontext(close_db)
    app.jinja_env.globals["csrf_token"] = csrf_token
    app.jinja_env.globals["today"] = lambda: date.today().isoformat()

    @app.before_request
    def load_user():
        """Memuat pengguna yang sedang login ke g.user (None bila belum login)."""
        g.user = None
        user_id = session.get("user_id")
        if user_id:
            g.user = User.get_by_id(get_db(), user_id)
            if g.user is None:  # akun sudah dihapus
                session.clear()

    app.before_request(csrf_protect)

    @app.template_filter("tgl")
    def format_tanggal(value):
        return value.strftime("%d %b %Y") if value else "-"

    # ---------- halaman error ----------
    def error_page(kode, judul, pesan):
        return render_template("error.html", kode=kode, judul=judul, pesan=pesan), kode

    @app.errorhandler(400)
    def e400(e):
        return error_page(400, "Permintaan tidak valid", "Sesi formulir kedaluwarsa. Muat ulang halaman lalu coba lagi.")

    @app.errorhandler(403)
    def e403(e):
        return error_page(403, "Akses ditolak", "Anda tidak memiliki izin untuk membuka halaman ini.")

    @app.errorhandler(404)
    def e404(e):
        return error_page(404, "Halaman tidak ditemukan", "Alamat yang Anda buka tidak tersedia.")

    @app.errorhandler(413)
    def e413(e):
        return error_page(413, "File terlalu besar", "Ukuran foto maksimal 2 MB.")

    @app.errorhandler(mysql.connector.Error)
    def edb(e):
        app.logger.error("Kesalahan database: %s", e)
        return error_page(500, "Database bermasalah",
                          "Aplikasi tidak dapat terhubung ke MySQL. Periksa file .env dan jalankan check_db.py.")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=Config.DEBUG)
