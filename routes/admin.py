from flask import Blueprint, render_template
from flask_login import login_required
from utils.decorators import admin_required
from models import db, User, Course

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    users_count = User.query.count()
    courses_count = Course.query.count()
    return render_template('dashboard/admin_dashboard.html', users_count=users_count, courses_count=courses_count)
