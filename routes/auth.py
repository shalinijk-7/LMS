from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Role
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import time
from datetime import datetime, timedelta
from utils.email import generate_otp, send_otp_email, send_2fa_otp_email

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handles the register functionality.
    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role_name = request.form.get('role', 'student') # Default to student
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login.', 'danger')
            return redirect(url_for('auth.login'))
            
        # Get role
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            # Create default roles if they don't exist
            role = Role(name=role_name)
            db.session.add(role)
            db.session.commit()
            
        # Create user
        user = User(
            name=name,
            email=email,
            role_id=role.id
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        from services.notification_service import notify_admins
        notify_admins(
            title="New User Registration",
            message=f"New {role.name} registered: {user.name} ({user.email})",
            notification_type='info',
            icon='bi-person-plus-fill',
            action_url='/admin/users'
        )
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles the login functionality.
    """
    if current_user.is_authenticated:
        return redirect_user_by_role(current_user)
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if user.two_factor_enabled or user.role.name in ['admin', 'instructor']:
                otp = generate_otp()
                user.otp_hash = generate_password_hash(otp)
                user.otp_expires_at = datetime.utcnow() + timedelta(minutes=5)
                user.otp_attempts = 0
                user.otp_last_sent_at = datetime.utcnow()
                db.session.commit()
                
                send_2fa_otp_email(user.email, otp)
                
                session['pre_2fa_user_id'] = user.id
                session['remember_me'] = remember
                session.modified = True
                return redirect(url_for('auth.verify_2fa'))

            login_user(user, remember=remember)
            flash('Logged in successfully.', 'success')
            
            # Redirect to next page or default role dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect_user_by_role(user)
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('auth/login.html')


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Handles the forgot password functionality.
    """
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            otp = generate_otp()
            # Store in session with 10 minute expiry
            session['reset_email'] = email
            session['reset_otp'] = otp
            session['otp_expiry'] = time.time() + 600
            session['otp_attempts'] = 0
            
            # Send email
            send_otp_email(email, otp)
            
            flash('An OTP has been sent to your email.', 'info')
            return redirect(url_for('auth.verify_otp'))
        else:
            flash('If an account exists with that email, a password reset link has been sent.', 'info')
    return render_template('auth/forgot_password.html')

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    """
    Handles the verify otp functionality.
    """
    if 'reset_email' not in session or 'reset_otp' not in session:
        flash('Invalid session. Please request a new password reset.', 'danger')
        return redirect(url_for('auth.forgot_password'))
        
    if request.method == 'POST':
        otp_input = request.form.get('otp')
        
        # Check expiry
        if time.time() > session.get('otp_expiry', 0):
            session.pop('reset_otp', None)
            flash('OTP has expired. Please request a new one.', 'danger')
            return redirect(url_for('auth.forgot_password'))
            
        # Check limit
        attempts = session.get('otp_attempts', 0)
        if attempts >= 3:
            session.clear()
            flash('Too many failed attempts. Please request a new OTP.', 'danger')
            return redirect(url_for('auth.forgot_password'))
            
        if otp_input == session.get('reset_otp'):
            session['otp_verified'] = True
            flash('OTP verified successfully.', 'success')
            return redirect(url_for('auth.reset_password'))
        else:
            session['otp_attempts'] = attempts + 1
            flash('Invalid OTP. Please try again.', 'danger')
            
    return render_template('auth/otp_verification.html')

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """
    Handles the reset password functionality.
    """
    if not session.get('otp_verified') or 'reset_email' not in session:
        flash('Please verify your OTP first.', 'danger')
        return redirect(url_for('auth.forgot_password'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        user = User.query.filter_by(email=session['reset_email']).first()
        if user:
            user.set_password(password)
            db.session.commit()
            
            # Clear session
            session.pop('reset_email', None)
            session.pop('reset_otp', None)
            session.pop('otp_expiry', None)
            session.pop('otp_attempts', None)
            session.pop('otp_verified', None)
            
            flash('Your password has been reset successfully.', 'success')
            return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html')

@auth_bp.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    """
    Handles the 2FA OTP verification functionality.
    """
    user_id = session.get('pre_2fa_user_id')
    if not user_id:
        flash('Invalid session. Please log in again.', 'danger')
        return redirect(url_for('auth.login'))
        
    user = User.query.get(user_id)
    if not user:
        session.pop('pre_2fa_user_id', None)
        flash('Invalid user. Please log in again.', 'danger')
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        otp_input = request.form.get('otp')
        
        if user.otp_attempts >= 3:
            session.pop('pre_2fa_user_id', None)
            user.otp_hash = None
            db.session.commit()
            flash('Too many failed attempts. Please log in again to receive a new OTP.', 'danger')
            return redirect(url_for('auth.login'))
            
        if user.otp_expires_at and datetime.utcnow() > user.otp_expires_at:
            flash('OTP has expired. Please request a new one.', 'danger')
            return render_template('auth/verify_2fa.html', expired=True)
            
        if user.otp_hash and check_password_hash(user.otp_hash, otp_input):
            # Success
            remember = session.get('remember_me', False)
            login_user(user, remember=remember)
            
            # Clean up
            user.otp_hash = None
            user.otp_expires_at = None
            user.otp_attempts = 0
            db.session.commit()
            
            session.pop('pre_2fa_user_id', None)
            session.pop('remember_me', None)
            
            flash('Two-Factor Authentication successful.', 'success')
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect_user_by_role(user)
        else:
            user.otp_attempts += 1
            db.session.commit()
            flash('Invalid OTP. Please try again.', 'danger')
            
    return render_template('auth/verify_2fa.html', expired=False)

@auth_bp.route('/resend-2fa', methods=['POST'])
def resend_2fa():
    """
    Handles resending the 2FA OTP.
    """
    user_id = session.get('pre_2fa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
        
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('auth.login'))
        
    # Check cooldown (60 seconds)
    if user.otp_last_sent_at and (datetime.utcnow() - user.otp_last_sent_at) < timedelta(seconds=60):
        flash('Please wait before requesting a new OTP.', 'warning')
        return redirect(url_for('auth.verify_2fa'))
        
    otp = generate_otp()
    user.otp_hash = generate_password_hash(otp)
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=5)
    user.otp_attempts = 0
    user.otp_last_sent_at = datetime.utcnow()
    db.session.commit()
    
    send_2fa_otp_email(user.email, otp)
    flash('A new OTP has been sent to your email.', 'info')
    
    return redirect(url_for('auth.verify_2fa'))

# --- Google OAuth Routes ---

@auth_bp.route('/login/google')
def google_login():
    """
    Handles the google login functionality.
    """
    oauth = current_app.extensions.get('authlib.integrations.flask_client')
    if not oauth:
        flash('OAuth is not configured properly.', 'danger')
        return redirect(url_for('auth.login'))
        
    redirect_uri = url_for('auth.google_authorize', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/authorize/google')
def google_authorize():
    """
    Handles the google authorize functionality.
    """
    oauth = current_app.extensions.get('authlib.integrations.flask_client')
    if not oauth:
        flash('OAuth is not configured properly.', 'danger')
        return redirect(url_for('auth.login'))
        
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        if not user_info:
            user_info = oauth.google.userinfo()
    except Exception as e:
        import traceback
        print("GOOGLE OAUTH ERROR:")
        print(traceback.format_exc())
        flash(f'Failed to log in with Google: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))
        
    email = user_info.get('email')
    name = user_info.get('name')
    
    user = User.query.filter_by(email=email).first()
    if not user:
        # Create new user, default to student role
        role = Role.query.filter_by(name='student').first()
        if not role:
            role = Role(name='student')
            db.session.add(role)
            db.session.commit()
            
        user = User(
            name=name,
            email=email,
            role_id=role.id
        )
        user.set_password(str(uuid.uuid4())) # Random password
        db.session.add(user)
        db.session.commit()
        
    if user.two_factor_enabled or user.role.name in ['admin', 'instructor']:
        otp = generate_otp()
        user.otp_hash = generate_password_hash(otp)
        user.otp_expires_at = datetime.utcnow() + timedelta(minutes=5)
        user.otp_attempts = 0
        user.otp_last_sent_at = datetime.utcnow()
        db.session.commit()
        
        send_2fa_otp_email(user.email, otp)
        
        session['pre_2fa_user_id'] = user.id
        session['remember_me'] = False
        session.modified = True
        return redirect(url_for('auth.verify_2fa'))
        
    login_user(user)
    flash('Logged in successfully via Google.', 'success')
    return redirect_user_by_role(user)

def redirect_user_by_role(user):
    """
    Handles the redirect user by role functionality.
    """
    if user.role.name == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif user.role.name == 'instructor':
        return redirect(url_for('instructor.dashboard'))
    else:
        return redirect(url_for('student.dashboard'))
