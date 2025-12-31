from flask import Blueprint, render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required

auth_bp = Blueprint("auth", __name__, template_folder="templates")

@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        phone = request.form["phone"]
        user = find_user_by_phone(phone)
        if user:
            login_user(user)
            return redirect(url_for(f"{user.role}.dashboard"))
        flash("Не найден пользователь с таким телефоном", "danger")
    return render_template("login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
