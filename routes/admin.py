"""
Admin Blueprint
Handles routing and views for administrative tasks, such as managing users, 
courses, and viewing platform reports.
"""
# Import core Flask components and decorator requirements
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required

# Import admin authorization checker
from utils.decorators import admin_required

# Import core models for platform entities
from models import db, User, Course

# Define the admin blueprint with its base URL prefix
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """
    Renders the admin dashboard with high-level platform statistics.
    
    Retrieves counts for users, courses, enrollments, and completions to
    display key metrics and calculate the average completion rate.
    
    Returns:
        Rendered HTML template for the admin dashboard.
    """
    # Fetch top-level metric counts for quick analysis
    users_count = User.query.count()
    courses_count = Course.query.count()
    
    # Import relational models locally to prevent potential circular dependency issues
    from models import Role, CourseCompletion, Enrollment
    
    # Locate specific database roles to filter different user segments
    instructor_role = Role.query.filter_by(name='instructor').first()
    student_role = Role.query.filter_by(name='student').first()
    
    # Retrieve user accounts mapped to instructor and student roles
    instructors = User.query.filter_by(role_id=instructor_role.id).all() if instructor_role else []
    students = User.query.filter_by(role_id=student_role.id).all() if student_role else []
    
    # Calculate totals for tracking user educational progress
    total_completions = CourseCompletion.query.count()
    total_enrollments = Enrollment.query.count()
    
    # Safely compute percentage to protect against division by zero errors
    avg_completion_rate = int((total_completions / total_enrollments) * 100) if total_enrollments > 0 else 0
    
    # Render the consolidated dashboard panel template passing statistics
    return render_template('dashboard/admin_dashboard.html', 
                           users_count=users_count, 
                           courses_count=courses_count,
                           instructors=instructors,
                           students=students,
                           total_completions=total_completions,
                           avg_completion_rate=avg_completion_rate)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """
    Displays a list of all registered users on the platform.
    
    Returns:
        Rendered HTML template for the admin user management page.
    """
    # Query all platform users ordered by registration date (newest first)
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('dashboard/admin_users.html', users=users)

@admin_bp.route('/courses')
@login_required
@admin_required
def courses():
    """
    Displays a list of all courses available on the platform.
    
    Returns:
        Rendered HTML template for the admin course management page.
    """
    # Query all created courses sorted chronologically
    courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template('dashboard/admin_courses.html', courses=courses)

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    """
    Generates and displays comprehensive reports in a datatable view.
    
    Returns:
        Rendered HTML template for the admin reports page.
    """
    # Local imports to fetch transactional tables and relationship data
    from models import Enrollment, Payment
    
    # Fetch enrollment history details
    enrollments = Enrollment.query.order_by(Enrollment.enrolled_at.desc()).all()
    
    report_data = []
    # Build complete reports payloads mapping enrollments to transaction payments
    for enr in enrollments:
        # Resolve payment associated with the active student and specific course
        payment = Payment.query.filter_by(student_id=enr.user_id, course_id=enr.course_id).first()
        
        # Evaluate status depending on existing invoice or fallback value for free resources
        payment_status = payment.status if payment else ('Free' if enr.course.course_type == 'Free' else 'Pending')
        
        # Populate formatted dataset dictionary
        report_data.append({
            'student_name': enr.student.name if enr.student else 'Unknown',
            'course_title': enr.course.title if enr.course else 'Unknown',
            'instructor_name': enr.course.instructor.name if enr.course and enr.course.instructor else 'Unknown',
            'course_type': enr.course.course_type if enr.course else 'Free',
            # Format date for cleaner layout display and keep ISO raw representation for data filtering
            'enrolled_at': enr.enrolled_at.strftime('%b %d, %Y<br>%I:%M %p') if enr.enrolled_at else 'Unknown',
            'raw_date': enr.enrolled_at.isoformat() if enr.enrolled_at else '1970-01-01',
            'payment_status': payment_status,
            'progress': enr.progress_percent,
            'amount': payment.amount if payment else 0.0,
            'completion_status': 'Completed' if enr.progress_percent == 100 else 'In Progress'
        })
        
    # Render final compiled analytical records
    return render_template('dashboard/admin_reports.html', report_data=report_data)
@admin_bp.route('/plans', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_plans():
    from models import SubscriptionPlan, Subscription, User, db
    if request.method == 'POST':
        plan_id = request.form.get('plan_id')
        if plan_id:
            plan = SubscriptionPlan.query.get(plan_id)
        else:
            plan = SubscriptionPlan()
            db.session.add(plan)
            
        plan.name = request.form.get('name')
        
        # Validation
        try:
            price = float(request.form.get('price', 0))
            if price < 0: raise ValueError('Price cannot be negative.')
            plan.price = price
            
            duration = int(request.form.get('duration_days', 30))
            if duration < 1: raise ValueError('Duration must be at least 1 day.')
            plan.duration_days = duration
            
            max_courses = int(request.form.get('max_courses', 5))
            if max_courses < -1: raise ValueError('Invalid courses limit.')
            plan.max_courses = max_courses
            
            max_students = int(request.form.get('max_students', 100))
            if max_students < -1: raise ValueError('Invalid students limit.')
            plan.max_students = max_students
            
            storage_limit = int(request.form.get('storage_limit_mb', 2000))
            if storage_limit < -1: raise ValueError('Invalid storage limit.')
            plan.storage_limit_mb = storage_limit
            
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('admin.manage_plans'))
            
        # Features Handling
        features_list = request.form.getlist('features')
        plan.features = ','.join(features_list)
        
        plan.has_advanced_analytics = request.form.get('has_advanced_analytics') == 'on'
        plan.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        flash('Subscription Plan saved successfully.', 'success')
        return redirect(url_for('admin.manage_plans'))
        
    plans = SubscriptionPlan.query.all()
    
    # Stats for Overview Cards
    total_plans = len(plans)
    active_plans = len([p for p in plans if p.is_active])
    total_active_subscribers = Subscription.query.filter_by(status='Active').count()
    active_trial_users = User.query.filter_by(trial_status='Trial Active').count()
    expired_trial_users = User.query.filter_by(trial_status='Trial Expired').count()
    
    return render_template(
        'dashboard/admin_plans.html', 
        plans=plans,
        total_plans=total_plans,
        active_plans=active_plans,
        total_active_subscribers=total_active_subscribers,
        active_trial_users=active_trial_users,
        expired_trial_users=expired_trial_users
    )

@admin_bp.route('/plans/subscribers/<int:plan_id>')
@login_required
@admin_required
def view_plan_subscribers(plan_id):
    from models import Subscription, SubscriptionPlan
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    subscribers = Subscription.query.filter_by(plan_id=plan.id).all()
    # Using the same dashboard template but rendering subscribers
    return render_template('dashboard/admin_plan_subscribers.html', plan=plan, subscribers=subscribers)


@admin_bp.route('/plans/toggle/<int:plan_id>', methods=['POST'])
@login_required
@admin_required
def toggle_plan(plan_id):
    from models import SubscriptionPlan, db
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    plan.is_active = not plan.is_active
    db.session.commit()
    status_msg = 'activated' if plan.is_active else 'deactivated'
    flash(f'Plan {plan.name} has been {status_msg}.', 'success')
    return redirect(url_for('admin.manage_plans'))
