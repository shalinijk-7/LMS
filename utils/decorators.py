from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user, logout_user

def role_required(*roles):
    """
    Handles the role required functionality.
    """
    def decorator(f):
        """
        Handles the decorator functionality.
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            """
            Handles the decorated function functionality.
            """
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role.name not in roles:
                logout_user()
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """
    Handles the admin required functionality.
    """
    return role_required('admin')(f)

def instructor_required(f):
    """
    Handles the instructor required functionality.
    """
    return role_required('instructor')(f)

def student_required(f):
    """
    Handles the student required functionality.
    """
    return role_required('student')(f)
