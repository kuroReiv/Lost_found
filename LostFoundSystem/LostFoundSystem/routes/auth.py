"""Registrasi, login, logout, dan profil (dipakai mahasiswa maupun admin)."""
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from models.user import User
from utils import get_db, login_required

bp = Blueprint("auth", __name__)


@bp.route("/")
def index():
    if g.user:
        return redirect(url_for(g.user.get_dashboard_endpoint()))  # polymorphism
    return redirect(url_for("auth.login"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for(g.user.get_dashboard_endpoint()))
    if request.method == "POST":
        try:
            User.register(
                get_db(),
                request.form.get("nama"),
                request.form.get("email"),
                request.form.get("password"),
                request.form.get("konfirmasi"),
            )
            flash("Registrasi berhasil. Silakan login.", "success")
            return redirect(url_for("auth.login"))
        except ValueError as e:
            flash(str(e), "danger")
    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for(g.user.get_dashboard_endpoint()))
    if request.method == "POST":
        user = User.login(get_db(), request.form.get("email"), request.form.get("password"))
        if user is None:
            flash("Email atau password salah.", "danger")
        else:
            session.clear()  # cegah session fixation
            session["user_id"] = user.user_id
            flash(f"Selamat datang, {user.nama}!", "success")
            return redirect(url_for(user.get_dashboard_endpoint()))
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Anda telah logout.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/profil", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        try:
            if request.form.get("aksi") == "password":
                g.user.change_password(
                    request.form.get("lama"), request.form.get("baru"), request.form.get("konfirmasi")
                )
                flash("Password berhasil diubah.", "success")
            else:
                g.user.update_profile(request.form.get("nama"), request.form.get("email"))
                flash("Profil berhasil diperbarui.", "success")
            return redirect(url_for("auth.profile"))
        except ValueError as e:
            flash(str(e), "danger")
    return render_template("profile.html")
