from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

partner_bp = Blueprint("partner", __name__, template_folder="templates/partner")

@partner_bp.before_request
def restrict_to_partners():
    if not current_user.is_authenticated or current_user.role != "partner":
        abort(403)

@partner_bp.route("/dashboard")
def dashboard():
    stats = get_partner_stats(current_user.id)
    return render_template("partner/dashboard.html", stats=stats)

@partner_bp.route("/boards")
def boards():
    boards = get_partner_boards(current_user.id)
    return render_template("partner/boards.html", boards=boards)
