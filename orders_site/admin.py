from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# Проверка прав администратора
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Доступ запрещен', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)

    return decorated_function


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')


# --- Партнёры ---
@admin_bp.route('/partners')
@admin_required
def partners():
    partners = db.get_all_partners()
    pending = [p for p in partners if not p['is_approved']]
    approved = [p for p in partners if p['is_approved']]
    return render_template('admin/partners.html',
                           pending=pending,
                           approved=approved)


@admin_bp.route('/approve-partner/<int:partner_id>')
@admin_required
def approve_partner(partner_id):
    db.approve_partner(partner_id)
    flash('Партнёр одобрен', 'success')
    return redirect(url_for('admin.partners'))


# --- Доски ---
@admin_bp.route('/boards')
@admin_required
def boards():
    all_boards = db.get_all_boards()
    locations = db.get_locations()
    return render_template('admin/boards.html',
                           boards=all_boards,
                           locations=locations)


@admin_bp.route('/add-board', methods=['POST'])
@admin_required
def add_board():
    name = request.form.get('name')
    description = request.form.get('description')
    total = int(request.form.get('total'))
    location_id = int(request.form.get('location_id'))

    db.add_board(name, description, total, location_id)
    flash('Доска добавлена', 'success')
    return redirect(url_for('admin.boards'))


# --- Бронирования ---
@admin_bp.route('/bookings')
@admin_required
def bookings():
    status = request.args.get('status', 'active')
    bookings_list = db.get_bookings_by_status(status)
    return render_template('admin/bookings.html',
                           bookings=bookings_list,
                           status=status)


@admin_bp.route('/cancel-booking/<int:booking_id>')
@admin_required
def cancel_booking(booking_id):
    db.cancel_booking(booking_id)
    flash('Бронирование отменено', 'success')
    return redirect(url_for('admin.bookings'))


# --- Финансы ---
@admin_bp.route('/finance')
@admin_required
def finance():
    today = datetime.now()
    week_ago = today - timedelta(days=7)

    stats = {
        'total': db.get_finance_stats(),
        'week': db.get_finance_stats(start_date=week_ago)
    }

    return render_template('admin/finance.html', stats=stats)


# --- Рассылка ---
@admin_bp.route('/mailing', methods=['GET', 'POST'])
@admin_required
def mailing():
    if request.method == 'POST':
        message = request.form.get('message')
        # Логика рассылки
        flash('Рассылка начата', 'info')
        return redirect(url_for('admin.mailing'))

    return render_template('admin/mailing.html')