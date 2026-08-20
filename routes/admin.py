"""
Admin Blueprint
Handles routing and views for administrative tasks such as managing users,
courses, and viewing platform reports.
"""
from datetime import datetime, timedelta
from collections import defaultdict

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func, desc
from utils.decorators import admin_required
from models import db, User, Course, Role, Enrollment
from models.all_models import CourseCompletion, ActivityLog, Lesson

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _role_map():
    return {r.name: r.id for r in Role.query.all()}


def _last_n_days_labels(n=14):
    today = datetime.utcnow().date()
    return [(today - timedelta(days=i)).strftime('%b %d') for i in range(n - 1, -1, -1)]


def _count_by_day(date_col, n=14):
    today = datetime.utcnow().date()
    start = datetime.combine(today - timedelta(days=n - 1), datetime.min.time())
    rows = (
        db.session.query(func.date(date_col).label('d'), func.count().label('c'))
        .filter(date_col >= start)
        .group_by(func.date(date_col))
        .all()
    )
    lookup = {str(r.d): r.c for r in rows}
    result = []
    for i in range(n - 1, -1, -1):
        day = (today - timedelta(days=i)).isoformat()
        result.append(lookup.get(day, 0))
    return result


def _is_paid(course):
    """Paid if price > 0, else Free."""
    try:
        return float(course.price or 0) > 0
    except Exception:
        return False


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    roles = _role_map()
    student_id = roles.get('student')
    instructor_id = roles.get('instructor')
    admin_id = roles.get('admin')

    users_count = User.query.count()
    students_count = User.query.filter_by(role_id=student_id).count() if student_id else 0
    instructors_count = User.query.filter_by(role_id=instructor_id).count() if instructor_id else 0
    admins_count = User.query.filter_by(role_id=admin_id).count() if admin_id else 0
    courses_count = Course.query.count()
    total_enrollments = Enrollment.query.count()
    total_completions = CourseCompletion.query.count()
    avg_completion_rate = (
        int((total_completions / total_enrollments) * 100) if total_enrollments else 0
    )

    all_courses = Course.query.all()
    paid_courses = sum(1 for c in all_courses if _is_paid(c))
    free_courses = courses_count - paid_courses

    total_revenue = 0.0
    revenue_month = 0.0
    revenue_by_day = [0] * 14
    recent_payments = []

    chart_labels = _last_n_days_labels(14)
    user_growth = _count_by_day(User.created_at, 14)
    enrollment_growth = _count_by_day(Enrollment.enrolled_at, 14)

    role_distribution = {
        'labels': ['Students', 'Instructors', 'Admins'],
        'data': [students_count, instructors_count, admins_count],
    }
    course_type_split = {
        'labels': ['Free', 'Paid'],
        'data': [free_courses, paid_courses],
    }

    top_courses_q = (
        db.session.query(
            Course.id,
            Course.title,
            Course.price,
            Course.thumbnail,
            func.count(Enrollment.id).label('enroll_count'),
            User.name.label('instructor_name'),
        )
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .outerjoin(User, User.id == Course.instructor_id)
        .group_by(Course.id)
        .order_by(desc('enroll_count'))
        .limit(6)
        .all()
    )
    top_courses = []
    for c in top_courses_q:
        price = float(c.price or 0)
        top_courses.append({
            'id': c.id,
            'title': c.title,
            'course_type': 'Paid' if price > 0 else 'Free',
            'price': price,
            'thumbnail': c.thumbnail,
            'enroll_count': c.enroll_count,
            'instructor_name': c.instructor_name or 'Unknown',
        })

    instructors = []
    if instructor_id:
        instr_users = User.query.filter_by(role_id=instructor_id).all()
        for instr in instr_users:
            course_ids = [c.id for c in Course.query.filter_by(instructor_id=instr.id).all()]
            course_count = len(course_ids)
            enroll_count = (
                Enrollment.query.filter(Enrollment.course_id.in_(course_ids)).count()
                if course_ids else 0
            )
            completion_count = (
                CourseCompletion.query.filter(CourseCompletion.course_id.in_(course_ids)).count()
                if course_ids else 0
            )
            instructors.append({
                'id': instr.id,
                'name': instr.name,
                'email': instr.email,
                'profile_photo': getattr(instr, 'profile_photo', None),
                'course_count': course_count,
                'enroll_count': enroll_count,
                'completion_count': completion_count,
                'revenue': 0.0,
                'completion_rate': (
                    int((completion_count / enroll_count) * 100) if enroll_count else 0
                ),
            })
        instructors.sort(key=lambda x: x['enroll_count'], reverse=True)

    recent_activity = (
        ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
    )
    recent_enrollments = (
        Enrollment.query.order_by(Enrollment.enrolled_at.desc()).limit(8).all()
    )

    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users_week = User.query.filter(User.created_at >= week_ago).count()
    new_enrollments_week = Enrollment.query.filter(Enrollment.enrolled_at >= week_ago).count()

    return render_template(
        'dashboard/admin_dashboard.html',
        users_count=users_count,
        students_count=students_count,
        instructors_count=instructors_count,
        admins_count=admins_count,
        courses_count=courses_count,
        total_enrollments=total_enrollments,
        total_completions=total_completions,
        avg_completion_rate=avg_completion_rate,
        total_revenue=total_revenue,
        paid_courses=paid_courses,
        free_courses=free_courses,
        new_users_week=new_users_week,
        new_enrollments_week=new_enrollments_week,
        revenue_month=revenue_month,
        chart_labels=chart_labels,
        user_growth=user_growth,
        enrollment_growth=enrollment_growth,
        revenue_by_day=revenue_by_day,
        role_distribution=role_distribution,
        course_type_split=course_type_split,
        top_courses=top_courses,
        instructors=instructors,
        recent_activity=recent_activity,
        recent_enrollments=recent_enrollments,
        recent_payments=recent_payments,
    )


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    stats = {
        'total': len(all_users),
        'students': sum(1 for u in all_users if u.role and u.role.name == 'student'),
        'instructors': sum(1 for u in all_users if u.role and u.role.name == 'instructor'),
        'admins': sum(1 for u in all_users if u.role and u.role.name == 'admin'),
        'verified': sum(1 for u in all_users if getattr(u, 'is_verified', False)),
        'unverified': sum(1 for u in all_users if not getattr(u, 'is_verified', False)),
    }
    chart_labels = _last_n_days_labels(14)
    user_growth = _count_by_day(User.created_at, 14)
    return render_template(
        'dashboard/admin_users.html',
        users=all_users,
        stats=stats,
        chart_labels=chart_labels,
        user_growth=user_growth,
    )


@admin_bp.route('/courses')
@login_required
@admin_required
def courses():
    courses_q = (
        db.session.query(
            Course,
            User.name.label('instructor_name'),
            func.count(Enrollment.id).label('enroll_count'),
        )
        .outerjoin(User, User.id == Course.instructor_id)
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .group_by(Course.id)
        .order_by(Course.created_at.desc())
        .all()
    )

    course_list = []
    total_enrollments = 0
    for row in courses_q:
        c = row.Course
        enroll_count = row.enroll_count or 0
        total_enrollments += enroll_count
        lesson_count = Lesson.query.filter_by(course_id=c.id).count()
        price = float(c.price or 0)
        c.course_type = 'Paid' if price > 0 else 'Free'
        course_list.append({
            'course': c,
            'instructor_name': row.instructor_name or 'Unknown',
            'enroll_count': enroll_count,
            'revenue': 0.0,
            'lesson_count': lesson_count,
        })

    stats = {
        'total': len(course_list),
        'free': sum(1 for x in course_list if not _is_paid(x['course'])),
        'paid': sum(1 for x in course_list if _is_paid(x['course'])),
        'total_enrollments': total_enrollments,
        'total_revenue': 0.0,
    }
    return render_template(
        'dashboard/admin_courses.html',
        courses=course_list,
        stats=stats,
    )


@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    enrollments = Enrollment.query.order_by(Enrollment.enrolled_at.desc()).all()
    report_data = []
    free_count = 0
    paid_count = 0

    for enr in enrollments:
        price = float(enr.course.price or 0) if enr.course else 0
        is_paid = price > 0
        course_type = 'Paid' if is_paid else 'Free'
        if is_paid:
            paid_count += 1
        else:
            free_count += 1

        report_data.append({
            'student_name': enr.student.name if enr.student else 'Unknown',
            'student_email': enr.student.email if enr.student else '',
            'course_title': enr.course.title if enr.course else 'Unknown',
            'instructor_name': (
                enr.course.instructor.name
                if enr.course and enr.course.instructor else 'Unknown'
            ),
            'course_type': course_type,
            'enrolled_at': (
                enr.enrolled_at.strftime('%b %d, %Y<br>%I:%M %p')
                if enr.enrolled_at else 'Unknown'
            ),
            'raw_date': enr.enrolled_at.isoformat() if enr.enrolled_at else '1970-01-01',
            'payment_status': course_type,
            'amount': price if is_paid else 0.0,
            'progress': enr.progress_percent or 0,
        })

    type_counts = defaultdict(int)
    for r in report_data:
        type_counts[r['course_type']] += 1

    status_counts = defaultdict(int)
    for r in report_data:
        status_counts[r['payment_status']] += 1

    chart_labels = _last_n_days_labels(14)
    enrollment_trend = _count_by_day(Enrollment.enrolled_at, 14)

    stats = {
        'total_enrollments': len(report_data),
        'success_payments': paid_count,
        'pending_payments': 0,
        'free_enrollments': free_count,
        'total_revenue': 0.0,
    }

    return render_template(
        'dashboard/admin_reports.html',
        report_data=report_data,
        stats=stats,
        chart_labels=chart_labels,
        enrollment_trend=enrollment_trend,
        type_labels=list(type_counts.keys()) or ['Free', 'Paid'],
        type_data=list(type_counts.values()) or [0, 0],
        status_labels=list(status_counts.keys()) or ['Free', 'Paid'],
        status_data=list(status_counts.values()) or [0, 0],
    )