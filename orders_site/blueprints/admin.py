from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

admin_bp = Blueprint("admin", __name__, template_folder="templates/admin")

@admin_bp.before_request
def restrict_to_admins():
    if not current_user.is_authenticated or current_user.role != "admin":
        abort(403)

@admin_bp.route("/dashboard")
def dashboard():
    # достаём из БД заявки партнёров, доски, брони...
    return render_template("admin/dashboard.html",
                           partners=get_pending_partners(),
                           boards=get_all_boards(),
                           bookings=get_all_bookings())

@admin_bp.route("/partners")
def partners():
    return render_template("admin/partners.html", partners=get_all_partners())
