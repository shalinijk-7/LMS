from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from utils.decorators import student_required, admin_required
from models import db, SubscriptionPlan, Subscription, User
from datetime import datetime, timedelta
import uuid

subscription_bp = Blueprint('subscription', __name__, url_prefix='/subscription')

@subscription_bp.route('/plans')
def plans():
    """Display available subscription plans and free trial option."""
    active_plans = SubscriptionPlan.query.filter_by(is_active=True).all()
    return render_template('subscription/plans.html', plans=active_plans)

@subscription_bp.route('/trial/start', methods=['POST'])
@login_required
@student_required
def start_trial():
    """Activate the 5-day free trial for the user."""
    user = User.query.get(current_user.id)
    
    if user.trial_used:
        flash('You have already used your free trial.', 'error')
        course_id = request.form.get('course_id')
        if course_id:
            return redirect(url_for('courses.course_details', course_id=course_id))
        return redirect(url_for('subscription.plans'))
        
    user.trial_started_at = datetime.utcnow()
    user.trial_ends_at = datetime.utcnow() + timedelta(days=5)
    user.trial_status = 'Trial Active'
    user.trial_used = True
    
    db.session.commit()
    
    # Notify student
    from services.notification_service import send_notification
    send_notification(
        user_id=user.id,
        title="Free Trial Started",
        message="Your 5-day free trial has been activated successfully! Enjoy access to selected features.",
        notification_type="success",
        icon="bi-gift-fill",
        action_url="/subscription/my-subscription"
    )
    
    flash('Your 5-day free trial has started!', 'success')
    
    course_id = request.form.get('course_id')
    if course_id:
        return redirect(url_for('courses.course_details', course_id=course_id))
        
    return redirect(url_for('subscription.my_subscription'))

@subscription_bp.route('/my-subscription')
@login_required
@student_required
def my_subscription():
    """Display the user's subscription and trial status."""
    user = User.query.get(current_user.id)
    
    # Check if trial has expired dynamically
    if user.trial_status == 'Trial Active' and user.trial_ends_at:
        if datetime.utcnow() > user.trial_ends_at:
            user.trial_status = 'Trial Expired'
            db.session.commit()
            
    # Get active subscription if any
    active_sub = Subscription.query.filter_by(user_id=user.id, status='Active').order_by(Subscription.end_date.desc()).first()
    
    if active_sub and active_sub.end_date < datetime.utcnow():
        active_sub.status = 'Expired'
        db.session.commit()
        active_sub = None
        
    # Get all past subscriptions for history
    sub_history = Subscription.query.filter_by(user_id=user.id).order_by(Subscription.start_date.desc()).all()
        
    # Calculate days remaining for trial
    trial_days_remaining = 0
    if user.trial_status == 'Trial Active' and user.trial_ends_at:
        delta = user.trial_ends_at - datetime.utcnow()
        trial_days_remaining = max(0, delta.days + (1 if delta.seconds > 0 else 0))
        
    return render_template('subscription/my_subscription.html', 
                           user=user, 
                           active_sub=active_sub, 
                           sub_history=sub_history,
                           trial_days_remaining=trial_days_remaining)

@subscription_bp.route('/dev/reset-trial')
@login_required
@student_required
def dev_reset_trial():
    """Development/testing only route to reset trial status for the current user."""
    user = User.query.get(current_user.id)
    user.trial_used = False
    user.trial_started_at = None
    user.trial_ends_at = None
    user.trial_status = None
    db.session.commit()
    flash('Development Mode: Your free trial has been completely reset.', 'info')
    return redirect(url_for('subscription.plans'))

@subscription_bp.route('/cancel', methods=['POST'])
@login_required
def cancel_sub():
    from models import Subscription
    active_sub = Subscription.query.filter_by(user_id=current_user.id, status='Active').order_by(Subscription.end_date.desc()).first()
    if active_sub:
        active_sub.status = 'Cancelled'
        db.session.commit()
        flash('Your subscription has been cancelled. You will retain access until the end of your billing cycle.', 'info')
    else:
        flash('No active subscription found.', 'error')
    
    if current_user.role.name == 'instructor':
        return redirect(url_for('instructor.subscription_management'))
    return redirect(url_for('subscription.my_subscription'))

@subscription_bp.route('/downgrade/<int:plan_id>')
@login_required
def downgrade_checkout(plan_id):
    from models import SubscriptionPlan
    from utils.helpers import get_instructor_usage
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    usage = get_instructor_usage(current_user.id)
    
    # Check if current usage is compatible with new plan limits
    if usage['courses_used'] > plan.max_courses or usage['students_used'] > plan.max_students or usage['storage_used_mb'] > plan.storage_limit_mb:
        flash('Your current usage exceeds the limits of the selected plan. Please reduce your usage before downgrading.', 'error')
        if current_user.role.name == 'instructor':
            return redirect(url_for('instructor.subscription_management'))
        return redirect(url_for('subscription.my_subscription'))
        
    return redirect(url_for('payment.checkout_plan', plan_id=plan.id))

@subscription_bp.route('/choose/<int:plan_id>')
def choose_plan(plan_id):
    """
    Handle the selection of a subscription plan from the public pricing page.
    As per explicit user requirements:
    - If authenticated, log out the user and redirect to the public landing page.
    - If not authenticated, preserve the selected plan and redirect to login to continue to checkout.
    """
    from flask import session
    from flask_login import logout_user
    from models import SubscriptionPlan
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    
    checkout_url = url_for('payment.checkout_plan', plan_id=plan.id)
    
    if current_user.is_authenticated:
        # Log out the user and redirect to public landing page pricing section
        logout_user()
        flash('You have been logged out to proceed with your subscription selection.', 'info')
        return redirect(url_for('subscription.plans'))
    else:
        # Guest Checkout allowed. Go directly to checkout.
        return redirect(checkout_url)
