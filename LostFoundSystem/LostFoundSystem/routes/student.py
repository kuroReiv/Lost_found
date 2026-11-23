"""Halaman khusus mahasiswa."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from models.claim import Claim
from models.item import Item
from models.report import ITEM_CLASSES, Report, buat_item
from utils import delete_foto, get_db, save_foto, to_int

bp = Blueprint("student", __name__, url_prefix="/mahasiswa")


@bp.before_request
def hanya_mahasiswa():
    """Penjaga: dijalankan sebelum SETIAP route di blueprint ini."""
    if g.user is None:
        flash("Silakan login terlebih dahulu.", "warning")
        return redirect(url_for("auth.login"))
    if g.user.role != "mahasiswa":
        abort(403)


@bp.route("/dashboard")
def dashboard():
    db = get_db()
    return render_template(
        "student/dashboard.html",
        ringkasan=Report(db).summary_by_user(g.user.user_id),
        klaim=Claim(db).count_by_claimant(g.user.user_id),
        terbaru=Report(db).search(limit=6),
    )


@bp.route("/laporan")
def semua_laporan():
    db = get_db()
    filters = {
        "q": request.args.get("q", "").strip(),
        "kategori": to_int(request.args.get("kategori")),
        "jenis": request.args.get("jenis", ""),
    }
    laporan = Report(db).search(filters["q"], filters["kategori"], filters["jenis"])
    return render_template(
        "student/laporan_list.html", laporan=laporan, kategori=Item.get_categories(db), filters=filters
    )


@bp.route("/laporan/saya")
def laporan_saya():
    laporan = Report(get_db()).search(user_id=g.user.user_id, limit=500)
    return render_template("student/laporan_saya.html", laporan=laporan)


@bp.route("/laporan/baru/<jenis>", methods=["GET", "POST"])
def buat_laporan(jenis):
    if jenis not in ITEM_CLASSES:
        abort(404)
    db = get_db()
    item = buat_item(jenis, db)  # LostItem / FoundItem (polymorphism)
    if request.method == "POST":
        foto = None
        try:
            foto = save_foto(request.files.get("foto"))
            Report(db).create(
                g.user.user_id, jenis, request.form.get("category_id"), request.form.get("nama_barang"),
                request.form.get("deskripsi"), request.form.get("lokasi"),
                request.form.get("tanggal_kejadian"), foto,
            )
            flash("Laporan berhasil dibuat.", "success")
            return redirect(url_for("student.laporan_saya"))
        except ValueError as e:
            delete_foto(foto)  # batalkan file yang sudah terlanjur tersimpan
            flash(str(e), "danger")
    return render_template(
        "student/laporan_form.html", item=item, kategori=Item.get_categories(db),
        data=request.form, mode="baru",
    )


@bp.route("/laporan/<int:report_id>")
def detail(report_id):
    db = get_db()
    laporan = Report(db).get_by_id(report_id) or abort(404)
    claim = Claim(db)
    milik_sendiri = laporan["user_id"] == g.user.user_id
    bisa_klaim = (
        laporan["jenis_laporan"] == "ditemukan" and laporan["status"] == "aktif"
        and not milik_sendiri and not claim.has_pending(report_id, g.user.user_id)
    )
    return render_template(
        "student/laporan_detail.html", laporan=laporan, milik_sendiri=milik_sendiri, bisa_klaim=bisa_klaim,
        dapat_diubah=milik_sendiri and Report(db).can_modify(laporan),
        klaim_saya=claim.get_by_report_and_claimant(report_id, g.user.user_id),
    )


@bp.route("/laporan/<int:report_id>/edit", methods=["GET", "POST"])
def edit(report_id):
    db = get_db()
    report = Report(db)
    laporan = report.get_by_id(report_id) or abort(404)
    if laporan["user_id"] != g.user.user_id:
        abort(403)
    if not report.can_modify(laporan):
        flash("Laporan sudah diproses dan tidak dapat diubah.", "warning")
        return redirect(url_for("student.detail", report_id=report_id))

    item = buat_item(laporan["jenis_laporan"], db)
    if request.method == "POST":
        foto_baru = None
        try:
            foto_baru = save_foto(request.files.get("foto"))
            foto_lama = report.update(
                report_id, g.user.user_id, request.form.get("category_id"), request.form.get("nama_barang"),
                request.form.get("deskripsi"), request.form.get("lokasi"),
                request.form.get("tanggal_kejadian"), foto_baru,
            )
            delete_foto(foto_lama)
            flash("Laporan berhasil diperbarui.", "success")
            return redirect(url_for("student.detail", report_id=report_id))
        except ValueError as e:
            delete_foto(foto_baru)
            flash(str(e), "danger")
    return render_template(
        "student/laporan_form.html", item=item, kategori=Item.get_categories(db),
        data=request.form if request.method == "POST" else laporan, mode="edit", laporan=laporan,
    )


@bp.route("/laporan/<int:report_id>/hapus", methods=["POST"])
def hapus(report_id):
    try:
        foto = Report(get_db()).delete(report_id, g.user.user_id)
        delete_foto(foto)
        flash("Laporan berhasil dihapus.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("student.laporan_saya"))


@bp.route("/laporan/<int:report_id>/klaim", methods=["POST"])
def ajukan_klaim(report_id):
    try:
        Claim(get_db()).create(report_id, g.user.user_id, request.form.get("alasan_klaim"))
        flash("Klaim berhasil diajukan. Tunggu verifikasi admin.", "success")
        return redirect(url_for("student.klaim_saya"))
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("student.detail", report_id=report_id))


@bp.route("/klaim")
def klaim_saya():
    return render_template("student/klaim_saya.html", klaim=Claim(get_db()).get_by_claimant(g.user.user_id))
