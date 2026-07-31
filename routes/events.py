from flask import request
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from models import db, Message, User

def register_events(socketio):
    @socketio.on('connect')
    def handle_connect():
        if current_user.is_authenticated:
            # User joins a room named after their own ID to receive private messages
            join_room(f'user_{current_user.id}')
            emit('status_change', {'user_id': current_user.id, 'status': 'online'}, broadcast=True)

    @socketio.on('disconnect')
    def handle_disconnect():
        if current_user.is_authenticated:
            emit('status_change', {'user_id': current_user.id, 'status': 'offline'}, broadcast=True)

    @socketio.on('join_course')
    def handle_join_course(data):
        course_id = data.get('course_id')
        if course_id:
            join_room(f'course_{course_id}')

    @socketio.on('leave_course')
    def handle_leave_course(data):
        course_id = data.get('course_id')
        if course_id:
            leave_room(f'course_{course_id}')

    @socketio.on('send_message')
    def handle_send_message(data):
        if not current_user.is_authenticated:
            return
            
        chat_type = data.get('type') # 'course' or 'user'
        chat_id = int(data.get('id'))
        content = data.get('content')
        file_url = data.get('file_url')
        
        msg = Message(sender_id=current_user.id, content=content, file_url=file_url)
        
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
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'chat_type': chat_type,
            'chat_id': chat_id
        }
        
        # Send to the target room
        emit('receive_message', message_data, room=room)
        # If private message, also send to the sender's own room so their UI updates if they have multiple tabs open
        if chat_type == 'user':
            emit('receive_message', message_data, room=f'user_{current_user.id}')
