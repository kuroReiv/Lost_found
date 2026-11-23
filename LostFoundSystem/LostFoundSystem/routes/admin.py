"""Halaman khusus admin."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from models.claim import Claim
from models.item import Item
from models.report import Report
from utils import get_db, to_int

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
def hanya_admin():
    """Mahasiswa yang mengetik alamat /admin/... akan mendapat 403."""
    if g.user is None:
        flash("Silakan login terlebih dahulu.", "warning")
        return redirect(url_for("auth.login"))
    if g.user.role != "admin":
        abort(403)


def _jalankan(aksi, pesan_sukses, *args):
    """Menjalankan aksi model; ValueError ditampilkan sebagai pesan."""
    try:
        aksi(*args)
        flash(pesan_sukses, "success")
    except ValueError as e:
        flash(str(e), "danger")


@bp.route("/dashboard")
def dashboard():
    db = get_db()
    return render_template(
        "admin/dashboard.html", stat=g.user.get_statistics(),
        klaim_terbaru=Claim(db).get_all("menunggu")[:5], laporan_terbaru=Report(db).search(limit=5),
    )


# ---------- laporan ----------
@bp.route("/laporan")
def laporan():
    db = get_db()
    filters = {
        "q": request.args.get("q", "").strip(), "kategori": to_int(request.args.get("kategori")),
        "jenis": request.args.get("jenis", ""), "status": request.args.get("status", ""),
    }
    data = Report(db).search(filters["q"], filters["kategori"], filters["jenis"], filters["status"], limit=300)
    return render_template(
        "admin/laporan.html", laporan=data, kategori=Item.get_categories(db),
        filters=filters, status_list=Report.STATUS_LIST,
    )


@bp.route("/laporan/<int:report_id>")
def laporan_detail(report_id):
    db = get_db()
    data = Report(db).get_by_id(report_id) or abort(404)
    return render_template(
        "admin/laporan_detail.html", laporan=data, klaim=Claim(db).get_by_report(report_id),
        status_list=Report.STATUS_LIST,
    )


@bp.route("/laporan/<int:report_id>/status", methods=["POST"])
def ubah_status(report_id):
    _jalankan(g.user.update_report_status, "Status laporan diperbarui.", report_id, request.form.get("status"))
    return redirect(url_for("admin.laporan_detail", report_id=report_id))


# ---------- kategori ----------
@bp.route("/kategori")
def kategori():
    return render_template("admin/kategori.html", kategori=g.user.get_categories_with_count())


@bp.route("/kategori/tambah", methods=["POST"])
def kategori_tambah():
    _jalankan(g.user.add_category, "Kategori ditambahkan.", request.form.get("nama_kategori"))
    return redirect(url_for("admin.kategori"))


@bp.route("/kategori/<int:category_id>/edit", methods=["POST"])
def kategori_edit(category_id):
    _jalankan(g.user.update_category, "Kategori diperbarui.", category_id, request.form.get("nama_kategori"))
    return redirect(url_for("admin.kategori"))


@bp.route("/kategori/<int:category_id>/hapus", methods=["POST"])
def kategori_hapus(category_id):
    _jalankan(g.user.delete_category, "Kategori dihapus.", category_id)
    return redirect(url_for("admin.kategori"))


# ---------- pengguna ----------
@bp.route("/pengguna")
def pengguna():
    return render_template("admin/pengguna.html", pengguna=g.user.list_users())


@bp.route("/pengguna/<int:user_id>/role", methods=["POST"])
def pengguna_role(user_id):
    _jalankan(g.user.change_user_role, "Role pengguna diperbarui.", user_id, request.form.get("role"))
    return redirect(url_for("admin.pengguna"))


@bp.route("/pengguna/<int:user_id>/hapus", methods=["POST"])
def pengguna_hapus(user_id):
    _jalankan(g.user.delete_user, "Pengguna dihapus.", user_id)
    return redirect(url_for("admin.pengguna"))


# ---------- klaim ----------
@bp.route("/klaim")
def klaim():
    status = request.args.get("status", "")
    return render_template(
        "admin/klaim.html", klaim=Claim(get_db()).get_all(status), status=status, status_list=Claim.STATUS_LIST
    )


def _aksi_klaim(aksi, pesan):
    _jalankan(aksi, pesan)  # aksi berupa lambda tanpa argumen
    return redirect(request.form.get("kembali") if request.form.get("kembali", "").startswith("/admin/")
                    else url_for("admin.klaim"))


@bp.route("/klaim/<int:claim_id>/setujui", methods=["POST"])
def klaim_setujui(claim_id):
    return _aksi_klaim(lambda: g.user.approve_claim(claim_id), "Klaim disetujui. Status laporan menjadi 'diklaim'.")


@bp.route("/klaim/<int:claim_id>/tolak", methods=["POST"])
def klaim_tolak(claim_id):
    return _aksi_klaim(lambda: g.user.reject_claim(claim_id), "Klaim ditolak.")


@bp.route("/klaim/<int:claim_id>/selesai", methods=["POST"])
def klaim_selesai(claim_id):
    return _aksi_klaim(lambda: g.user.complete_claim(claim_id), "Klaim selesai. Barang ditandai sudah dikembalikan.")
