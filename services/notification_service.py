from models import db, Notification

def send_notification(user_id, title, message, notification_type='info', icon='bi-info-circle', action_url=None, sender_id=None):
    """
    Handles the send notification functionality.
    """
    from app import socketio
    """
    Creates a notification in the database and emits it via Socket.IO to the specific user.
    """
    # 1. Save to database
    notification = Notification(
        user_id=user_id,
        sender_id=sender_id,
        title=title,
        message=message,
        notification_type=notification_type,
        icon=icon,
        action_url=action_url
    )
    db.session.add(notification)
    db.session.commit()
    
    # 2. Emit real-time event
    notification_data = {
        'id': notification.id,
        'title': notification.title,
        'message': notification.message,
        'type': notification.notification_type,
        'icon': notification.icon,
        'action_url': notification.action_url,
        'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    print(f"Emitting new_notification to user_{user_id}: {notification_data['title']}")
    socketio.emit('new_notification', notification_data, room=f'user_{user_id}')
    
    return notification

def notify_admins(title, message, notification_type='info', icon='bi-info-circle', action_url=None, sender_id=None):
    """
    Sends a notification to all users with the 'admin' role.
    """
    from models import Role
    
    admin_roles = Role.query.filter(Role.name.ilike('admin')).all()
    if not admin_roles:
        return
        
    for admin_role in admin_roles:
        for admin in admin_role.users:
            send_notification(
                user_id=admin.id,
                title=title,
                message=message,
                notification_type=notification_type,
                icon=icon,
                action_url=action_url,
                sender_id=sender_id
            )

