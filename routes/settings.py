# Handles user profile and application settings.
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Setting, User

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Handle profile photo upload
        photo_file = request.files.get('profile_photo')
        if photo_file and photo_file.filename != '':
            import os
            import time
            from werkzeug.utils import secure_filename
            from flask import current_app
            filename = secure_filename(photo_file.filename)
            filename = f"profile_{current_user.id}_{int(time.time())}_{filename}"
            
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profiles')
            os.makedirs(upload_dir, exist_ok=True)
            
            photo_file.save(os.path.join(upload_dir, filename))
            current_user.profile_photo = f"profiles/{filename}"
            
        # Update basic info
        current_user.name = request.form.get('name')
        current_user.phone = request.form.get('phone')
        current_user.bio = request.form.get('bio')
        
        # Update settings
        if not current_user.settings:
            current_user.settings = Setting(user_id=current_user.id)
        
        # Theme (only allow valid themes)
        theme = request.form.get('theme', 'default')
        if theme not in ['default', 'dark', 'ocean', 'forest']:
            theme = 'default'
        current_user.settings.theme = theme

        current_user.settings.language = request.form.get('language', 'en')
        current_user.settings.email_notifications_enabled = True if request.form.get('email_notifications') else False
        current_user.settings.desktop_notifications_enabled = True if request.form.get('desktop_notifications') else False
        current_user.settings.real_time_notifications_enabled = True if request.form.get('real_time_notifications') else False
        current_user.settings.notification_sound_enabled = True if request.form.get('notification_sound') else False
        
        db.session.commit()
        flash('Settings updated successfully.', 'success')
        return redirect(url_for('settings.profile'))
        
    return render_template('settings/profile.html')


@settings_bp.route('/update_notif_pref', methods=['POST'])
@login_required
def update_notif_pref():
    data = request.get_json()
    if not current_user.settings:
        current_user.settings = Setting(user_id=current_user.id)
    
    if 'desktop' in data:
        current_user.settings.desktop_notifications_enabled = data['desktop']
        
    db.session.commit()
    return {'status': 'success'}


@settings_bp.route('/update_theme', methods=['POST'])
@login_required
def update_theme():
    data = request.get_json()
    if not data or 'theme' not in data:
        return {'status': 'error'}, 400

    theme = data['theme']
    allowed = ['default', 'dark', 'ocean', 'forest']
    if theme not in allowed:
        theme = 'default'

    if not current_user.settings:
        current_user.settings = Setting(user_id=current_user.id)

    current_user.settings.theme = theme
    db.session.commit()
    return {'status': 'success', 'theme': theme}