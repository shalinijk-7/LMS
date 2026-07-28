from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Assignment
from models import Course
from models import db

assignment_bp = Blueprint('assignment', __name__, url_prefix='/assignment')

@assignment_bp.route('/course/<int:course_id>')
@login_required
def list_assignments(course_id):
    course = Course.query.get_or_404(course_id)
    assignments = Assignment.query.filter_by(course_id=course.id).all()
    return render_template('assignments/assignment_list.html', course=course, assignments=assignments)

@assignment_bp.route('/view/<int:assignment_id>')
@login_required
def view_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    return render_template('assignments/view_assignment.html', assignment=assignment)
