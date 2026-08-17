from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user, logout_user

def role_required(*roles):
    """
    Decorator factory to restrict access to routes based on user role.
    
    Args:
        *roles: A variable length list of role names allowed to access the route.
        
    Returns:
        function: The actual decorator function.
    """
    def decorator(f):
        """
        The actual decorator that wraps the view function.
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            """
            Wrapper function that checks user authentication and authorization.
            Redirects to login if unauthorized.
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
    Decorator to enforce that the current user has the 'admin' role.
    """
    return role_required('admin')(f)

def instructor_required(f):
    """
    Decorator to enforce that the current user has the 'instructor' role.
    """
    return role_required('instructor')(f)

def student_required(f):
    """
    Decorator to enforce that the current user has the 'student' role.
    """
    return role_required('student')(f)
