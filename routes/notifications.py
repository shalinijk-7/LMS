from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Notification
from models import db

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@notifications_bp.route('/')
@login_required
def index():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('settings/notifications.html', notifications=notifications)

@notifications_bp.route('/mark-read/<int:notif_id>')
@login_required
def mark_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id == current_user.id:
        notif.is_read = True
        db.session.commit()
    return redirect(url_for('notifications.index'))
