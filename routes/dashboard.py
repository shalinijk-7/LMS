# Import necessary Flask and authentication modules
from flask import Blueprint
from flask_login import login_required, current_user
from routes.auth import redirect_user_by_role

# Initialize the Blueprint for dashboard-related routes
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    """
    Acts as a universal router for all 'Back to Dashboard' buttons.
    Automatically redirects the user to their specific role dashboard.
    This simplifies navigation by providing a single endpoint for returning to the main view.
    """
    # Redirect the currently authenticated user based on their assigned role
    return redirect_user_by_role(current_user)