# Handles user notifications throughout the application.
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import Notification, Setting, db

notifications_bp = Blueprint(
    'notifications',
    __name__,
    url_prefix='/notifications'
)


@notifications_bp.route('/')
@login_required
def index():
    """Show all notifications for the current user."""
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).all()
    return render_template('settings/notifications.html', notifications=notifications)


@notifications_bp.route('/test')
@login_required
def test_notif():
    """Send a test notification (useful for debugging)."""
    from services.notification_service import send_notification
    send_notification(
        user_id=current_user.id,
        title="System Update",
        message="Your real-time notification system is working perfectly!",
        notification_type="success",
        icon="bi-check-circle-fill",
        action_url="/notifications"
    )
    return jsonify({"status": "Notification sent! Check your other tabs."})


@notifications_bp.route('/mark-read/<int:notif_id>', methods=['POST', 'GET'])
@login_required
def mark_read(notif_id):
    """Mark a single notification as read."""
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id == current_user.id:
        notif.is_read = True
        db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'status': 'success'})

    if notif.action_url:
        return redirect(notif.action_url)
    return redirect(url_for('notifications.index'))


@notifications_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    """Mark all notifications of the current user as read."""
    Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).update({'is_read': True})
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'status': 'success'})
    return redirect(url_for('notifications.index'))


@notifications_bp.route('/clear-all', methods=['POST'])
@login_required
def clear_all():
    """Delete all notifications of the current user."""
    Notification.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'status': 'success'})
    return redirect(url_for('notifications.index'))


@notifications_bp.route('/recent')
@login_required
def recent():
    """Return the 15 most recent notifications as JSON."""
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).limit(15).all()

    notifs_data = []
    for n in notifications:
        notifs_data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.notification_type,
            'icon': n.icon,
            'action_url': n.action_url,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%Y-%m-%dT%H:%M:%S')
        })
    return jsonify({'notifications': notifs_data})