from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Role
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import time
from datetime import datetime, timedelta
from utils.email import generate_otp, send_otp_email, send_2fa_otp_email

# Define the authentication blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Route to handle user registration.
    Accepts GET requests to render the registration form.
    Accepts POST requests to process new user sign-ups, create default roles if needed,
    hash passwords, notify administrators, and redirect to login.
    """
    # Redirect already logged-in users to the main page
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
            
        # Get role or dynamically create it if it does not exist in the database
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
        
        # Send notification to administrators about the new registration
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
    Route to handle user login.
    Accepts GET requests to render the login form.
    Accepts POST requests to authenticate user credentials.
    Supports standard login and redirects to Two-Factor Authentication (2FA) if enabled or required by role.
    """
    # If already logged in, redirect them immediately to their dashboard
    if current_user.is_authenticated:
        return redirect_user_by_role(current_user)
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        
        # Verify credentials
        if user and user.check_password(password):
            # Enforce 2FA if user explicitly enabled it, or if they have privileged roles (admin/instructor)
            if user.two_factor_enabled or user.role.name in ['admin', 'instructor']:
                otp = generate_otp()
                user.otp_hash = generate_password_hash(otp)
                user.otp_expires_at = datetime.utcnow() + timedelta(minutes=5)
                user.otp_attempts = 0
                user.otp_last_sent_at = datetime.utcnow()
                db.session.commit()
                
                # Deliver the 2FA token
                send_2fa_otp_email(user.email, otp)
                
                # Store temporary user identity in session before authorization is finalized
                session['pre_2fa_user_id'] = user.id
                session['remember_me'] = remember
                session.modified = True
                return redirect(url_for('auth.verify_2fa'))

            # Standard password login for users without 2FA
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
    Route to handle password recovery requests.
    Accepts POST requests to generate and send an OTP to the user's email for password reset.
    Stores the reset state and OTP securely in the user session.
    """
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            otp = generate_otp()
            # Store verification details in session with 10 minute expiry
            session['reset_email'] = email
            session['reset_otp'] = otp
            session['otp_expiry'] = time.time() + 600
            session['otp_attempts'] = 0
            
            # Send email
            send_otp_email(email, otp)
            
            flash('An OTP has been sent to your email.', 'info')
            return redirect(url_for('auth.verify_otp'))
        else:
            # Avoid user enumeration by flashing a generic success-style message
            flash('If an account exists with that email, a password reset link has been sent.', 'info')
    return render_template('auth/forgot_password.html')

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    """
    Route to handle OTP verification for password resets.
    Validates the submitted OTP against the session-stored OTP.
    Enforces time expiry and rate-limiting (max 3 attempts).
    """
    # Prevent direct access to verification without a valid reset flow session
    if 'reset_email' not in session or 'reset_otp' not in session:
        flash('Invalid session. Please request a new password reset.', 'danger')
        return redirect(url_for('auth.forgot_password'))
        
    if request.method == 'POST':
        otp_input = request.form.get('otp')
        
        # Check expiry of OTP code
        if time.time() > session.get('otp_expiry', 0):
            session.pop('reset_otp', None)
            flash('OTP has expired. Please request a new one.', 'danger')
            return redirect(url_for('auth.forgot_password'))
            
        # Enforce rate-limiting of 3 failed attempts to prevent brute forcing
        attempts = session.get('otp_attempts', 0)
        if attempts >= 3:
            session.clear()
            flash('Too many failed attempts. Please request a new OTP.', 'danger')
            return redirect(url_for('auth.forgot_password'))
            
        # Match OTP input against stored OTP code
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
    Route to handle final password reset.
    Allows users to set a new password only after successful OTP verification.
    Clears the reset session data upon completion.
    """
    # Verify that the OTP has been successfully verified before permitting access
    if not session.get('otp_verified') or 'reset_email' not in session:
        flash('Please verify your OTP first.', 'danger')
        return redirect(url_for('auth.forgot_password'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        user = User.query.filter_by(email=session['reset_email']).first()
        if user:
            user.set_password(password)
            db.session.commit()
            
            # Clear reset session parameters
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
    Route to handle 2FA OTP verification during login.
    Verifies the OTP sent to the user's email.
    Logs the user in upon success or enforces rate limiting on failed attempts.
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
        
        # Enforce rate-limiting of 3 failed attempts on 2FA
        if user.otp_attempts >= 3:
            session.pop('pre_2fa_user_id', None)
            user.otp_hash = None
            db.session.commit()
            flash('Too many failed attempts. Please log in again to receive a new OTP.', 'danger')
            return redirect(url_for('auth.login'))
            
        # Verify that the 2FA token has not expired
        if user.otp_expires_at and datetime.utcnow() > user.otp_expires_at:
            flash('OTP has expired. Please request a new one.', 'danger')
            return render_template('auth/verify_2fa.html', expired=True)
            
        # Check security token verification via password-hash utilities
        if user.otp_hash and check_password_hash(user.otp_hash, otp_input):
            # Log user in upon successful verification
            remember = session.get('remember_me', False)
            login_user(user, remember=remember)
            
            # Reset security parameters on success
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
    Route to handle resending the 2FA OTP.
    Includes a 60-second cooldown mechanism to prevent spam.
    """
    user_id = session.get('pre_2fa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
        
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('auth.login'))
        
    # Check cooldown (60 seconds) to prevent excessive email generation
    if user.otp_last_sent_at and (datetime.utcnow() - user.otp_last_sent_at) < timedelta(seconds=60):
        flash('Please wait before requesting a new OTP.', 'warning')
        return redirect(url_for('auth.verify_2fa'))
        
    # Regenerate OTP and record the dispatch metadata
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
    Route to initiate the Google OAuth 2.0 login flow.
    Redirects the user to Google's consent screen.
    """
    oauth = current_app.extensions.get('authlib.integrations.flask_client')
    if not oauth:
        flash('OAuth is not configured properly.', 'danger')
        return redirect(url_for('auth.login'))
        
    # Build dynamically external callback redirection URL
    redirect_uri = url_for('auth.google_authorize', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/authorize/google')
def google_authorize():
    """
    Callback route for Google OAuth 2.0.
    Retrieves user information from Google, creates a new user if they don't exist,
    and initiates the 2FA flow or logs them in directly.
    """
    oauth = current_app.extensions.get('authlib.integrations.flask_client')
    if not oauth:
        flash('OAuth is not configured properly.', 'danger')
        return redirect(url_for('auth.login'))
        
    try:
        # Retrieve tokens and user data via identity provider callbacks
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
        # Allocate random UUID password for accounts initialized via OAuth logins
        user.set_password(str(uuid.uuid4()))
        db.session.add(user)
        db.session.commit()
        
    # Enforce 2FA during OAuth flow if user has enabled it or belongs to privileged groups
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
        
    # Finalize login session
    login_user(user)
    flash('Logged in successfully via Google.', 'success')
    return redirect_user_by_role(user)

def redirect_user_by_role(user):
    """
    Helper function to route authenticated users to their respective dashboards
    based on their assigned role (Admin, Instructor, or Student).
    """
    # Check identity privileges to resolve destination page
    if user.role.name == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif user.role.name == 'instructor':
        return redirect(url_for('instructor.dashboard'))
    else:
        return redirect(url_for('student.dashboard'))