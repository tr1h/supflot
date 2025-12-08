from flask import Blueprint, render_template
from flask_login import login_required, current_user

user_bp = Blueprint("user", __name__, template_folder="templates/user")

@user_bp.before_request
@login_required
def before():
    pass

@user_bp.route("/dashboard")
def dashboard():
    bonuses = calculate_bonuses(current_user.id)
    return render_template("user/dashboard.html", bonuses=bonuses)

@user_bp.route("/bookings")
def bookings():
    history = get_user_bookings(current_user.id)
    return render_template("user/bookings.html", bookings=history)
