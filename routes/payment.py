from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from utils.decorators import student_required
from models import db, Course, Payment, PurchaseHistory, Enrollment
from datetime import datetime
import uuid

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')

@payment_bp.route('/checkout/<int:course_id>')
@login_required
@student_required
def checkout(course_id):
    """
    Handles the checkout functionality.
    Prepares the checkout page for a specific course, including tax calculation.
    Directly enrolls the student if the course is free.
    """

    course = Course.query.get_or_404(course_id)
    
    from utils.helpers import get_instructor_usage
    usage = get_instructor_usage(course.instructor_id)
    if not usage['students_ok']:
        flash('This course has reached its maximum student capacity.', 'error')
        return redirect(url_for('courses.course_details', course_id=course.id))
    
    if course.course_type == 'Free':
        flash('This course is free. You can enroll directly.', 'info')
        return redirect(url_for('courses.course_details', course_id=course.id))
        
    # Check if already enrolled
    existing = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    if existing:
        flash('You are already enrolled in this course.', 'info')
        return redirect(url_for('student.dashboard'))
        
    tax = round(course.price * 0.05, 2) # 5% tax example
    total_amount = round(course.price + tax, 2)
        
    return render_template('payment/checkout.html', course=course, tax=tax, total_amount=total_amount)

@payment_bp.route('/process/<int:course_id>', methods=['POST'])
@login_required
@student_required
def process_payment(course_id):
    """
    Handles the process payment functionality.
    Simulates payment processing, creates payment and purchase history records,
    enrolls the student in the course, and sends notifications.
    """

    course = Course.query.get_or_404(course_id)
    payment_method = request.form.get('payment_method', 'Card')
    coupon_code = request.form.get('coupon_code', '').strip()
    
    # Simulate a successful payment processing
    transaction_id = str(uuid.uuid4()).upper().replace('-', '')[:16]
    
    discount_amount = 0.0
    from models import Coupon
    
    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code, is_active=True).first()
        is_valid = True
        
        if not coupon: is_valid = False
        elif coupon.expiry_date and coupon.expiry_date < datetime.utcnow(): is_valid = False
        elif coupon.usage_limit and coupon.times_used >= coupon.usage_limit: is_valid = False
        elif coupon.min_purchase_amount and course.price < coupon.min_purchase_amount: is_valid = False
        elif coupon.course_id and coupon.course_id != course.id: is_valid = False
        elif coupon.instructor_id and coupon.instructor_id != course.instructor_id: is_valid = False
        
        if is_valid:
            if coupon.discount_type == 'fixed':
                discount_amount = round(coupon.discount_fixed_amount, 2)
            else:
                discount_amount = round(course.price * (coupon.discount_percentage / 100.0), 2)
            
            if discount_amount > course.price:
                discount_amount = course.price
                
            coupon.times_used += 1
    
    discounted_price = course.price - discount_amount
    tax = round(discounted_price * 0.05, 2)
    total_amount = round(discounted_price + tax, 2)
    
    # 1. Create Payment record
    new_payment = Payment(
        student_id=current_user.id,
        course_id=course.id,
        amount=total_amount,
        currency=course.currency,
        payment_method=payment_method,
        transaction_id=transaction_id,
        status='Success',
        coupon_code=coupon_code if discount_amount > 0 else None,
        discount_amount=discount_amount
    )
    db.session.add(new_payment)
    db.session.flush() # to get new_payment.id
    
    # 2. Create Purchase History
    new_purchase = PurchaseHistory(
        student_id=current_user.id,
        course_id=course.id,
        payment_id=new_payment.id
    )
    db.session.add(new_purchase)
    
    # 3. Enroll Student
    new_enrollment = Enrollment(user_id=current_user.id, course_id=course.id)
    db.session.add(new_enrollment)
    
    # 4. Notify Instructor
    from services.notification_service import send_notification
    send_notification(
        user_id=course.instructor_id,
        title="New Course Sale",
        message=f"{current_user.name} just purchased '{course.title}'.",
        notification_type="success",
        icon="bi-currency-exchange",
        action_url="/instructor/dashboard"
    )
    
    send_notification(
        user_id=current_user.id,
        title="Payment Successful",
        message=f"You have successfully purchased and enrolled in '{course.title}'.",
        notification_type="success",
        icon="bi-bag-check-fill",
        action_url=f"/courses/{course.id}/start"
    )
    
    db.session.commit()
    
    flash('Payment successful! You are now enrolled.', 'success')
    return redirect(url_for('payment.success', transaction_id=transaction_id))

@payment_bp.route('/plan/checkout/<int:plan_id>')
def checkout_plan(plan_id):
    """
    Handles checkout for a subscription plan.
    """
    from models import SubscriptionPlan
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    if not plan.is_active:
        flash('This plan is no longer available.', 'error')
        return redirect(url_for('subscription.plans'))
    
    tax = round(plan.price * 0.05, 2)
    total_amount = round(plan.price + tax, 2)
    
    return render_template('payment/checkout.html', plan=plan, tax=tax, total_amount=total_amount, is_plan=True)

@payment_bp.route('/plan/process/<int:plan_id>', methods=['POST'])
def process_plan_payment(plan_id):
    """
    Processes payment for a subscription plan.
    """
    from models import SubscriptionPlan, Subscription
    from datetime import timedelta
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    payment_method = request.form.get('payment_method', 'Card')
    coupon_code = request.form.get('coupon_code', '').strip()
    
    transaction_id = str(uuid.uuid4()).upper().replace('-', '')[:16]
    
    discount_amount = 0.0
    from models import Coupon
    
    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code, is_active=True).first()
        is_valid = True
        
        if not coupon: is_valid = False
        elif coupon.expiry_date and coupon.expiry_date < datetime.utcnow(): is_valid = False
        elif coupon.usage_limit and coupon.times_used >= coupon.usage_limit: is_valid = False
        elif coupon.min_purchase_amount and plan.price < coupon.min_purchase_amount: is_valid = False
        elif coupon.course_id or coupon.instructor_id: is_valid = False # Plans are global
        
        if is_valid:
            if coupon.discount_type == 'fixed':
                discount_amount = round(coupon.discount_fixed_amount, 2)
            else:
                discount_amount = round(plan.price * (coupon.discount_percentage / 100.0), 2)
            
            if discount_amount > plan.price:
                discount_amount = plan.price
                
            coupon.times_used += 1
                
    discounted_price = plan.price - discount_amount
    tax = round(discounted_price * 0.05, 2)
    total_amount = round(discounted_price + tax, 2)
    
    if current_user.is_authenticated:
        new_payment = Payment(
            student_id=current_user.id,
            plan_id=plan.id,
            amount=total_amount,
            currency=plan.currency,
            payment_method=payment_method,
            transaction_id=transaction_id,
            status='Success',
            coupon_code=coupon_code if discount_amount > 0 else None,
            discount_amount=discount_amount
        )
        db.session.add(new_payment)
        db.session.flush()
        
        new_purchase = PurchaseHistory(
            student_id=current_user.id,
            plan_id=plan.id,
            payment_id=new_payment.id
        )
        db.session.add(new_purchase)
        
        # Activate subscription
        active_subs = Subscription.query.filter_by(user_id=current_user.id, status='Active').all()
        
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=plan.duration_days)
        
        for sub in active_subs:
            if sub.plan_id == plan.id:
                if sub.end_date > datetime.utcnow():
                    start_date = sub.end_date
                    end_date = start_date + timedelta(days=plan.duration_days)
            sub.status = 'Cancelled'
            sub.end_date = datetime.utcnow()
            
        new_sub = Subscription(
            user_id=current_user.id,
            plan_id=plan.id,
            start_date=start_date,
            end_date=end_date,
            status='Active'
        )
        db.session.add(new_sub)
        
        # Also end free trial if active
        from models import User
        user = User.query.get(current_user.id)
        if user.trial_status == 'Trial Active':
            user.trial_status = 'Trial Expired'
            user.trial_ends_at = datetime.utcnow()
            
        from services.notification_service import send_notification
        send_notification(
            user_id=current_user.id,
            title="Subscription Activated",
            message=f"You have successfully subscribed to the {plan.name} plan.",
            notification_type="success",
            icon="bi-star-fill",
            action_url="/subscription/my-subscription"
        )
        
        from services.email_service import send_subscription_success_email
        send_subscription_success_email(
            student=user,
            plan=plan,
            payment=new_payment,
            subscription=new_sub
        )
        
        db.session.commit()
    else:
        # GUEST CHECKOUT
        from flask import session
        session['guest_payment'] = {
            'plan_id': plan.id,
            'amount': total_amount,
            'currency': plan.currency,
            'payment_method': payment_method,
            'transaction_id': transaction_id,
            'status': 'Success',
            'coupon_code': coupon_code if discount_amount > 0 else None,
            'discount_amount': discount_amount,
            'duration_days': plan.duration_days,
            'plan_name': plan.name,
            'billing_email': request.form.get('billing_email')
        }
    
    flash(f'Payment successful! Your {plan.name} subscription is active.', 'success')
    return redirect(url_for('payment.success', transaction_id=transaction_id))

@payment_bp.route('/success/<transaction_id>')
def success(transaction_id):
    """
    Handles the success functionality.
    Displays a success page and receipt details for a completed payment transaction.
    """
    if current_user.is_authenticated:
        payment = Payment.query.filter_by(transaction_id=transaction_id).first_or_404()
        
        # Ensure current user is the owner
        if payment.student_id != current_user.id:
            flash('Unauthorized access.', 'error')
            return redirect(url_for('student.dashboard'))
    else:
        from flask import session
        guest_payment = session.get('guest_payment')
        if not guest_payment or guest_payment['transaction_id'] != transaction_id:
            flash('Invalid transaction or session expired.', 'error')
            return redirect(url_for('index'))
        payment = None
        
    return render_template('payment/success.html', payment=payment, transaction_id=transaction_id)

from flask import jsonify

@payment_bp.route('/apply_coupon', methods=['POST'])
@login_required
def apply_coupon():
    data = request.get_json()
    code = data.get('code')
    amount = float(data.get('amount', 0))
    course_id = data.get('course_id')
    
    if not code or not amount:
        return jsonify({'success': False, 'message': 'Invalid request'})
        
    from models import Coupon, Course
    coupon = Coupon.query.filter_by(code=code, is_active=True).first()
    
    if not coupon:
        return jsonify({'success': False, 'message': 'Invalid coupon code'})
        
    if coupon.expiry_date and coupon.expiry_date < datetime.utcnow():
        return jsonify({'success': False, 'message': 'Coupon has expired'})
        
    if coupon.usage_limit and coupon.times_used >= coupon.usage_limit:
        return jsonify({'success': False, 'message': 'Coupon usage limit reached'})
        
    if coupon.min_purchase_amount and amount < coupon.min_purchase_amount:
        return jsonify({'success': False, 'message': f'Minimum purchase of {coupon.min_purchase_amount} required'})
        
    # Check applicability
    if course_id:
        course = Course.query.get(course_id)
        if course:
            if coupon.course_id and coupon.course_id != int(course_id):
                return jsonify({'success': False, 'message': 'Coupon is not applicable to this course'})
            if coupon.instructor_id and coupon.instructor_id != course.instructor_id:
                return jsonify({'success': False, 'message': 'Coupon is not applicable to this course'})
    elif coupon.course_id or coupon.instructor_id:
        # If paying for a plan but coupon is for a course/instructor
        return jsonify({'success': False, 'message': 'Coupon is not applicable for subscription plans'})
        
    # Calculate discount
    if coupon.discount_type == 'fixed':
        discount = round(coupon.discount_fixed_amount, 2)
        message = f'Coupon applied! {discount} off.'
    else:
        discount = round(amount * (coupon.discount_percentage / 100.0), 2)
        message = f'Coupon applied! {coupon.discount_percentage}% off.'
        
    # Ensure discount does not exceed amount
    if discount > amount:
        discount = amount
        
    return jsonify({
        'success': True,
        'discount': discount,
        'message': message
    })

@payment_bp.route('/invoice/<transaction_id>')
@login_required
def invoice(transaction_id):
    payment = Payment.query.filter_by(transaction_id=transaction_id).first_or_404()
    if payment.student_id != current_user.id and current_user.role.name != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('student.dashboard'))
        
    return render_template('payment/invoice.html', payment=payment)

@payment_bp.route('/refund/<transaction_id>', methods=['POST'])
@login_required
def process_refund(transaction_id):
    if current_user.role.name not in ['admin', 'instructor']:
        flash('Unauthorized.', 'error')
        return redirect(url_for('student.dashboard'))
        
    payment = Payment.query.filter_by(transaction_id=transaction_id).first_or_404()
    
    if payment.status == 'Refunded':
        flash('Payment is already refunded.', 'info')
        return redirect(request.referrer or url_for('instructor.dashboard'))
        
    payment.status = 'Refunded'
    payment.refund_status = 'Completed'
    payment.refund_date = datetime.utcnow()
    
    # Revoke access
    if payment.course_id:
        enrollment = Enrollment.query.filter_by(user_id=payment.student_id, course_id=payment.course_id).first()
        if enrollment:
            db.session.delete(enrollment)
            
    if payment.plan_id:
        from models import Subscription
        sub = Subscription.query.filter_by(user_id=payment.student_id, plan_id=payment.plan_id, status='Active').first()
        if sub:
            sub.status = 'Cancelled'
            sub.end_date = datetime.utcnow()
            
    from services.notification_service import send_notification
    send_notification(
        user_id=payment.student_id,
        title="Payment Refunded",
        message=f"Your payment ({payment.transaction_id}) has been refunded and access revoked.",
        notification_type="info",
        icon="bi-arrow-counterclockwise",
        action_url="/student/payment-history"
    )
    
    db.session.commit()
    flash('Refund processed successfully.', 'success')
    return redirect(request.referrer or url_for('instructor.dashboard'))
