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

            if not current_user.role or current_user.role.name not in roles:
                flash('You do not have permission to access this page.', 'danger')
                if current_user.is_authenticated and current_user.role:
                    if current_user.role.name == 'admin':
                        return redirect(url_for('admin.dashboard'))
                    elif current_user.role.name == 'instructor':
                        return redirect(url_for('instructor.dashboard'))
                    else:
                        return redirect(url_for('student.dashboard'))
                return redirect(url_for('auth.login'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Only admin."""
    return role_required('admin')(f)


def instructor_required(f):
    """Only instructor (admin cannot enter)."""
    return role_required('instructor')(f)


def student_required(f):
    """Only student (admin/instructor cannot enter)."""
    return role_required('student')(f)
