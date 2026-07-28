from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Setting, User

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Update basic info
        current_user.name = request.form.get('name')
        current_user.phone = request.form.get('phone')
        current_user.bio = request.form.get('bio')
        
        # Update settings
        if not current_user.settings:
            current_user.settings = Setting(user_id=current_user.id)
            
        current_user.settings.theme = request.form.get('theme', 'light')
        current_user.settings.language = request.form.get('language', 'en')
        current_user.settings.notification_prefs = True if request.form.get('notifications') else False
        
        db.session.commit()
        flash('Settings updated successfully.', 'success')
        return redirect(url_for('settings.profile'))
        
    return render_template('settings/profile.html')
