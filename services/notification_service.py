"""
Notification Service Module

Handles real-time and persistent notifications for users and administrators
using Socket.IO for live emission and SQLAlchemy for database storage.
"""
from models import db, Notification

def send_notification(user_id, title, message, notification_type='info', icon='bi-info-circle', action_url=None, sender_id=None):
    """
    Creates a notification in the database and emits it via Socket.IO to a specific user.
    
    Args:
        user_id (int): The ID of the recipient user.
        title (str): The brief title of the notification.
        message (str): The detailed content of the notification.
        notification_type (str, optional): Category of notification (e.g., 'info', 'success', 'warning'). Defaults to 'info'.
        icon (str, optional): Bootstrap icon class to display. Defaults to 'bi-info-circle'.
        action_url (str, optional): URL to redirect the user when they click the notification. Defaults to None.
        sender_id (int, optional): The ID of the user who triggered the notification, if applicable. Defaults to None.
        
    Returns:
        Notification: The created Notification database model instance.
    """
    from app import socketio
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
    Sends a notification to all users who possess the 'admin' role.
    
    Queries the database for all users associated with the 'admin' role and 
    dispatches an individual notification to each of them using `send_notification`.
    
    Args:
        title (str): The brief title of the notification.
        message (str): The detailed content of the notification.
        notification_type (str, optional): Category of notification. Defaults to 'info'.
        icon (str, optional): Bootstrap icon class to display. Defaults to 'bi-info-circle'.
        action_url (str, optional): URL to redirect the admin when they click the notification. Defaults to None.
        sender_id (int, optional): The ID of the user who triggered the notification, if applicable. Defaults to None.
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

