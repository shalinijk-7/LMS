from flask import request
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from models import db, Message, User, MessageReaction, Course
from services.notification_service import send_notification

def get_room_name(chat_type, chat_id):
    """
    Handles the get room name functionality.
    """
    if chat_type == 'course':
        return f'course_{chat_id}'
    elif chat_type == 'user':
        return f'user_{chat_id}'
    return None

def register_events(socketio):
    """
    Handles the register events functionality.
    """
    @socketio.on('connect')
    def handle_connect():
        """
        Handles the handle connect functionality.
        """
        if current_user.is_authenticated:
            join_room(f'user_{current_user.id}')
            print(f"DEBUG: User {current_user.id} ({current_user.email}) CONNECTED and joined room user_{current_user.id}")
            emit('status_change', {'user_id': current_user.id, 'status': 'online'}, broadcast=True)
        else:
            print("DEBUG: Anonymous user CONNECTED to socket.")

    @socketio.on('disconnect')
    def handle_disconnect():
        """
        Handles the handle disconnect functionality.
        """
        if current_user.is_authenticated:
            print(f"DEBUG: User {current_user.id} DISCONNECTED")
            emit('status_change', {'user_id': current_user.id, 'status': 'offline'}, broadcast=True)

    @socketio.on('join_course')
    def handle_join_course(data):
        """
        Handles the handle join course functionality.
        """
        course_id = data.get('course_id')
        if course_id:
            join_room(f'course_{course_id}')

    @socketio.on('leave_course')
    def handle_leave_course(data):
        """
        Handles the handle leave course functionality.
        """
        course_id = data.get('course_id')
        if course_id:
            leave_room(f'course_{course_id}')

    @socketio.on('typing')
    def handle_typing(data):
        """
        Handles the handle typing functionality.
        """
        if not current_user.is_authenticated: return
        room = get_room_name(data.get('type'), data.get('id'))
        if room:
            emit('user_typing', {'user_id': current_user.id, 'user_name': current_user.name, 'chat_type': data.get('type'), 'chat_id': data.get('id')}, room=room, include_self=False)

    @socketio.on('stop_typing')
    def handle_stop_typing(data):
        """
        Handles the handle stop typing functionality.
        """
        if not current_user.is_authenticated: return
        room = get_room_name(data.get('type'), data.get('id'))
        if room:
            emit('user_stop_typing', {'user_id': current_user.id, 'chat_type': data.get('type'), 'chat_id': data.get('id')}, room=room, include_self=False)

    @socketio.on('send_message')
    def handle_send_message(data):
        """
        Handles the handle send message functionality.
        """
        print(f"DEBUG: handle_send_message TRIGGERED by user {current_user.id if current_user.is_authenticated else 'Anonymous'}: {data}")
        if not current_user.is_authenticated: return
        
        chat_type = data.get('type')
        chat_id = int(data.get('id'))
        content = data.get('content')
        file_url = data.get('file_url')
        message_type = data.get('message_type', 'text')
        reply_to_id = data.get('reply_to_id')
        is_announcement = data.get('is_announcement', False)
        
        msg = Message(sender_id=current_user.id, content=content, file_url=file_url, message_type=message_type, reply_to_id=reply_to_id, is_announcement=is_announcement)
        
        if chat_type == 'course':
            msg.course_id = chat_id
            room = f'course_{chat_id}'
        elif chat_type == 'user':
            msg.receiver_id = chat_id
            room = f'user_{chat_id}'
        else:
            return

        db.session.add(msg)
        db.session.commit()
        
        message_data = {
            'id': msg.id,
            'sender_id': msg.sender_id,
            'sender_name': current_user.name,
            'content': msg.content,
            'file_url': msg.file_url,
            'message_type': msg.message_type,
            'is_announcement': msg.is_announcement,
            'reply_to_id': msg.reply_to_id,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'chat_type': chat_type,
            'chat_id': chat_id,
            'is_edited': False,
            'is_deleted': False,
            'is_pinned': False,
            'reactions': []
        }
        
        emit('receive_message', message_data, room=room)
        
        # Send Notification
        if chat_type == 'user':
            emit('receive_message', message_data, room=f'user_{current_user.id}')
            
            notif_data = {
                'id': msg.id,
                'title': current_user.name,
                'message': f"New Message: \"{msg.content[:30]}...\"",
                'type': 'primary',
                'icon': 'bi-chat-dots',
                'action_url': f'/chat?user={current_user.id}'
            }
            emit('new_notification', notif_data, room=f'user_{msg.receiver_id}')
            
            # Notify the receiver (and sender for testing)
            # if msg.receiver_id != current_user.id:
            send_notification(
                user_id=msg.receiver_id,
                title=current_user.name,
                message=f"New Message: \"{msg.content[:30]}...\"",
                notification_type='primary',
                icon='bi-chat-dots',
                action_url=f'/chat?user={current_user.id}',
                sender_id=current_user.id
            )
        elif chat_type == 'course':
            course = Course.query.get(chat_id)
            course_name = course.title if course else f"Course {chat_id}"
            
            # Find all enrolled students and the instructor to notify
            from models import Enrollment
            if course:
                users_to_notify = [e.user_id for e in Enrollment.query.filter_by(course_id=chat_id).all()]
                if course.instructor_id not in users_to_notify:
                    users_to_notify.append(course.instructor_id)
                
                for uid in users_to_notify:
                    # if uid != current_user.id:
                    notif_title = f"{course_name}"
                    notif_msg = f"New Group Message from {current_user.name}"
                    if is_announcement:
                        notif_msg = f"Instructor posted a new announcement."
                        
                    notif_data = {
                        'title': notif_title,
                        'message': notif_msg,
                        'type': 'info',
                        'icon': 'bi-chat-text',
                        'action_url': f'/chat?course={chat_id}'
                    }
                    emit('new_notification', notif_data, room=f'user_{uid}')
                        
                    send_notification(
                        user_id=uid,
                        title=notif_title,
                        message=notif_msg,
                        notification_type='info',
                        icon='bi-chat-text',
                        action_url=f'/chat?course={chat_id}',
                        sender_id=current_user.id
                    )

    @socketio.on('edit_message')
    def handle_edit_message(data):
        """
        Handles the handle edit message functionality.
        """
        if not current_user.is_authenticated: return
        msg = Message.query.get(data.get('message_id'))
        if msg and msg.sender_id == current_user.id:
            msg.content = data.get('new_content')
            msg.is_edited = True
            db.session.commit()
            
            chat_type = 'course' if msg.course_id else 'user'
            chat_id = msg.course_id if msg.course_id else msg.receiver_id
            room = get_room_name(chat_type, chat_id)
            
            emit('message_edited', {'message_id': msg.id, 'new_content': msg.content, 'chat_type': chat_type, 'chat_id': chat_id}, room=room)
            if chat_type == 'user':
                emit('message_edited', {'message_id': msg.id, 'new_content': msg.content, 'chat_type': chat_type, 'chat_id': chat_id}, room=f'user_{current_user.id}')

    @socketio.on('delete_message')
    def handle_delete_message(data):
        """
        Handles the handle delete message functionality.
        """
        if not current_user.is_authenticated: return
        msg = Message.query.get(data.get('message_id'))
        if msg and msg.sender_id == current_user.id:
            msg.is_deleted = True
            msg.content = "This message was deleted."
            msg.file_url = None
            db.session.commit()
            
            chat_type = 'course' if msg.course_id else 'user'
            chat_id = msg.course_id if msg.course_id else msg.receiver_id
            room = get_room_name(chat_type, chat_id)
            
            emit('message_deleted', {'message_id': msg.id, 'chat_type': chat_type, 'chat_id': chat_id}, room=room)
            if chat_type == 'user':
                emit('message_deleted', {'message_id': msg.id, 'chat_type': chat_type, 'chat_id': chat_id}, room=f'user_{current_user.id}')

    @socketio.on('react_message')
    def handle_react_message(data):
        """
        Handles the handle react message functionality.
        """
        if not current_user.is_authenticated: return
        msg_id = data.get('message_id')
        emoji = data.get('emoji')
        
        msg = Message.query.get(msg_id)
        if not msg: return
        
        existing = MessageReaction.query.filter_by(message_id=msg_id, user_id=current_user.id, emoji=emoji).first()
        if existing:
            db.session.delete(existing)
            action = 'removed'
        else:
            new_reaction = MessageReaction(message_id=msg_id, user_id=current_user.id, emoji=emoji)
            db.session.add(new_reaction)
            action = 'added'
        db.session.commit()
        
        chat_type = 'course' if msg.course_id else 'user'
        chat_id = msg.course_id if msg.course_id else (msg.receiver_id if msg.sender_id == current_user.id else msg.sender_id)
        room = get_room_name(chat_type, chat_id)
        
        payload = {'message_id': msg_id, 'emoji': emoji, 'user_id': current_user.id, 'action': action, 'chat_type': chat_type, 'chat_id': chat_id}
        if room: emit('message_reacted', payload, room=room)
        if chat_type == 'user':
            emit('message_reacted', payload, room=f'user_{msg.sender_id}')
            emit('message_reacted', payload, room=f'user_{msg.receiver_id}')

    @socketio.on('pin_message')
    def handle_pin_message(data):
        """
        Handles the handle pin message functionality.
        """
        if not current_user.is_authenticated: return
        msg_id = data.get('message_id')
        msg = Message.query.get(msg_id)
        if not msg: return
        
        msg.is_pinned = not msg.is_pinned
        db.session.commit()
        
        chat_type = 'course' if msg.course_id else 'user'
        chat_id = msg.course_id if msg.course_id else (msg.receiver_id if msg.sender_id == current_user.id else msg.sender_id)
        room = get_room_name(chat_type, chat_id)
        
        payload = {'message_id': msg.id, 'is_pinned': msg.is_pinned, 'chat_type': chat_type, 'chat_id': chat_id}
        if room: emit('message_pinned', payload, room=room)
        if chat_type == 'user':
            emit('message_pinned', payload, room=f'user_{msg.sender_id}')
            emit('message_pinned', payload, room=f'user_{msg.receiver_id}')
