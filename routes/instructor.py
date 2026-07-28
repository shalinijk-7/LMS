from flask import Blueprint, render_template
from flask_login import login_required, current_user
from utils.decorators import instructor_required
from models import db, Course

instructor_bp = Blueprint('instructor', __name__, url_prefix='/instructor')

@instructor_bp.route('/dashboard')
@login_required
@instructor_required
def dashboard():
    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    return render_template('dashboard/instructor_dashboard.html', courses=courses)
