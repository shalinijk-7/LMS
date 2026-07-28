from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import db, Enrollment

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/dashboard')
@login_required
def dashboard():
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard/student_dashboard.html', enrollments=enrollments)
