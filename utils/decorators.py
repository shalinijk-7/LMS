from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role.name not in roles:
                flash('You do not have permission to access this page.', 'danger')
                # Redirect to their specific dashboard
                if current_user.role.name == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif current_user.role.name == 'instructor':
                    return redirect(url_for('instructor.dashboard'))
                else:
                    return redirect(url_for('student.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    return role_required('admin')(f)

def instructor_required(f):
    return role_required('instructor', 'admin')(f)
