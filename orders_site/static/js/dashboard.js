@app.route('/dashboard')
@login_required
def dashboard():
    role = current_user.role.split('|')[0]
    if role == 'admin':
        return render_template('admin_dashboard.html')
    elif role == 'partner':
        return render_template('partner_dashboard.html')
    else:
        return render_template('user_dashboard.html')