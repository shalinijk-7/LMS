// static/js/chat_enhanced.js
document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    // DOM Elements
    const chatSidebar = document.getElementById('chatSidebar');
    const chatMain = document.getElementById('chatMain');
    const chatItems = document.querySelectorAll('.chat-item');
    const chatMessagesContainer = document.getElementById('chat-messages');
    const chatInputBox = document.getElementById('chat-input-box');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const chatForm = document.getElementById('chat-form');
    
    // Header & Info Panel
    const chatTitle = document.getElementById('chat-title');
    const chatSubtitle = document.getElementById('chat-subtitle');
    const chatHeaderAvatar = document.getElementById('chat-header-avatar');
    const chatHeaderActions = document.getElementById('chatHeaderActions');
    const toggleInfoPanelBtn = document.getElementById('toggleInfoPanel');
    const chatInfoPanel = document.getElementById('chatInfoPanel');
    const mobileBackBtn = document.getElementById('mobileBackBtn');
    
    // Search & Filters
    const globalChatSearch = document.getElementById('globalChatSearch');
    const filterBtns = document.querySelectorAll('.filter-btn');
    const toggleMessageSearch = document.getElementById('toggleMessageSearch');
    const messageSearchBar = document.getElementById('messageSearchBar');
    const closeMessageSearch = document.getElementById('closeMessageSearch');
    const messageSearchInput = document.getElementById('messageSearchInput');
    
    // Form Inputs
    const activeChatTypeInput = document.getElementById('active-chat-type');
    const activeChatIdInput = document.getElementById('active-chat-id');
    const editMessageIdInput = document.getElementById('edit-message-id');
    const replyToIdInput = document.getElementById('reply-to-id');
    const isAnnouncementInput = document.getElementById('is-announcement');
    const sendIcon = document.getElementById('sendIcon');
    
    // Attachments & Emojis
    const emojiPickerBtn = document.getElementById('emojiPickerBtn');
    const emojiPickerContainer = document.getElementById('emojiPickerContainer');
    const fileUploadInput = document.getElementById('fileUploadInput');
    const attachImageBtn = document.getElementById('attachImageBtn');
    const attachDocumentBtn = document.getElementById('attachDocumentBtn');
    const toggleAnnouncementBtn = document.getElementById('toggleAnnouncementBtn');
    
    // Reply / Pinned UI
    const replyPreviewBar = document.getElementById('replyPreviewBar');
    const replyToName = document.getElementById('replyToName');
    const replyToText = document.getElementById('replyToText');
    const cancelReplyBtn = document.getElementById('cancelReplyBtn');
    const pinnedMessagesBar = document.getElementById('pinnedMessagesBar');
    
    let currentPinnedMessages = [];
    let typingTimeout = null;
    let isTyping = false;

    // --- Core Chat Initialization ---
    chatItems.forEach(item => {
        item.addEventListener('click', () => {
            const chatType = item.getAttribute('data-chat-type');
            const chatId = item.getAttribute('data-chat-id');
            const chatName = item.getAttribute('data-chat-title');
            
            // UI Updates
            chatItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            
            // Mobile toggle
            if (window.innerWidth <= 767) {
                chatSidebar.classList.add('hide-mobile');
            }
            
            // Header Update
            chatTitle.textContent = chatName;
            chatHeaderAvatar.textContent = chatName.charAt(0);
            chatHeaderAvatar.classList.remove('d-none');
            chatSubtitle.classList.remove('d-none');
            chatHeaderActions.classList.remove('d-none');
            
            // Form Reset
            activeChatTypeInput.value = chatType;
            activeChatIdInput.value = chatId;
            chatInputBox.disabled = false;
            cancelEditOrReply();
            
            // Join Room
            if (chatType === 'course') {
                socket.emit('join_course', { course_id: chatId });
                chatSubtitle.innerHTML = 'Group Chat';
            } else {
                chatSubtitle.innerHTML = '<span class="status-dot bg-secondary d-inline-block rounded-circle me-1" style="width:8px; height:8px;"></span>Offline';
            }
            
            // Clear unread badge
            const badge = item.querySelector('.unread-badge');
            if(badge) { badge.classList.add('d-none'); badge.textContent = '0'; }
            
            loadChatHistory(chatType, chatId);
            loadInfoPanel(chatType, chatId);
        });
    });

    mobileBackBtn.addEventListener('click', () => {
        chatSidebar.classList.remove('hide-mobile');
    });

    // --- Loading Data ---
    /**
     * Handles the loadChatHistory functionality.
     */
    function loadChatHistory(type, id) {
        chatMessagesContainer.innerHTML = `
            <div class="m-auto text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-2 text-muted">Loading messages...</p>
            </div>
        `;
        
        fetch(`/chat/history/${type}/${id}`)
            .then(res => res.json())
            .then(messages => {
                chatMessagesContainer.innerHTML = '';
                currentPinnedMessages = [];
                
                if (messages.length === 0) {
                    chatMessagesContainer.innerHTML = `
                        <div class="m-auto text-muted text-center py-5">
                            <p>No messages yet. Start the conversation!</p>
                        </div>
                    `;
                } else {
                    let lastDate = null;
                    messages.forEach(msg => {
                        // Date separator logic
                        const msgDate = new Date(msg.timestamp).toLocaleDateString();
                        if (msgDate !== lastDate) {
                            chatMessagesContainer.insertAdjacentHTML('beforeend', `<div class="text-center my-3"><span class="badge bg-light text-muted border">${msgDate}</span></div>`);
                            lastDate = msgDate;
                        }
                        
                        if (msg.is_pinned) {
                            currentPinnedMessages.push(msg);
                        }
                        
                        chatMessagesContainer.insertAdjacentHTML('beforeend', createMessageHTML(msg));
                    });
                    scrollToBottom();
                }
                updatePinnedBar();
            })
            .catch(err => {
                console.error(err);
                chatMessagesContainer.innerHTML = '<div class="alert alert-danger m-auto">Error loading messages.</div>';
            });
    }

    /**
     * Handles the loadInfoPanel functionality.
     */
    function loadInfoPanel(type, id) {
        const infoContent = document.getElementById('infoContent');
        const infoTitle = document.getElementById('infoTitle');
        const infoAvatar = document.getElementById('infoAvatar');
        const infoSubtitle = document.getElementById('infoSubtitle');
        
        fetch(`/chat/info/${type}/${id}`)
            .then(res => res.json())
            .then(data => {
                if(type === 'course') {
                    infoTitle.textContent = data.title;
                    infoAvatar.textContent = data.title.charAt(0);
                    infoSubtitle.textContent = `Instructor: ${data.instructor}`;
                    infoContent.innerHTML = `
                        <div class="mb-4">
                            <h6 class="fw-bold">Course Info</h6>
                            <p class="text-muted small">${data.description || 'No description provided.'}</p>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span class="text-muted"><i class="bi bi-people me-2"></i>Students</span>
                            <span class="fw-bold">${data.total_students}</span>
                        </div>
                    `;
                } else {
                    infoTitle.textContent = data.name;
                    infoAvatar.textContent = data.name.charAt(0);
                    infoSubtitle.textContent = data.role;
                    infoContent.innerHTML = `
                        <div class="d-flex justify-content-between mb-2">
                            <span class="text-muted"><i class="bi bi-envelope me-2"></i>Email</span>
                            <span class="fw-bold small">${data.email}</span>
                        </div>
                    `;
                }
            });
    }

    // --- Message Rendering ---
    /**
     * Handles the createMessageHTML functionality.
     */
    function createMessageHTML(msg) {
        const isMe = msg.sender_id === CURRENT_USER_ID;
        const alignClass = isMe ? 'justify-content-end' : 'justify-content-start';
        const bubbleClass = isMe ? 'message-out' : 'message-in';
        
        if (msg.is_announcement) {
            return `
                <div class="message-row d-flex flex-column w-100 px-2" id="msg-${msg.id}">
                    <div class="message-announcement text-center">
                        <h6 class="fw-bold text-warning mb-2"><i class="bi bi-megaphone-fill me-2"></i>Announcement from ${msg.sender_name}</h6>
                        <p class="mb-1">${msg.is_deleted ? '<em>This announcement was deleted.</em>' : escapeHTML(msg.content)}</p>
                        <small class="text-muted" style="font-size:0.7rem;">${msg.timestamp}</small>
                    </div>
                </div>
            `;
        }

        let fileHTML = '';
        if (msg.file_url && !msg.is_deleted) {
            const ext = msg.file_url.split('.').pop().toLowerCase();
            if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) {
                fileHTML = `<div class="attachment-preview"><img src="${msg.file_url}" alt="Attachment"></div>`;
            } else if (['mp4', 'webm', 'ogg'].includes(ext)) {
                fileHTML = `<div class="attachment-preview"><video src="${msg.file_url}" controls class="w-100 rounded"></video></div>`;
            } else {
                fileHTML = `
                    <a href="${msg.file_url}" target="_blank" class="file-card">
                        <i class="bi bi-file-earmark-text-fill"></i>
                        <span class="text-truncate">Attachment.${ext}</span>
                    </a>
                `;
            }
        }

        let contentHTML = msg.is_deleted ? 'This message was deleted.' : escapeHTML(msg.content);
        const editedTag = msg.is_edited && !msg.is_deleted ? '<span class="msg-edited-tag">(edited)</span>' : '';
        const deletedClass = msg.is_deleted ? 'msg-deleted' : '';
        
        let replyHTML = '';
        if (msg.reply_to_id && !msg.is_deleted) {
            replyHTML = `
                <div class="reply-badge mb-1 p-1 rounded" style="background: rgba(0,0,0,0.1); font-size: 0.75rem; border-left: 3px solid #ccc; cursor: pointer;" onclick="scrollToMessage(${msg.reply_to_id})">
                    <i class="bi bi-reply-fill"></i> Replying to message...
                </div>
            `;
        }
        
        // Reactions
        let reactionsHTML = '<div class="reactions-container">';
        if (msg.reactions && msg.reactions.length > 0) {
            const reactionCounts = {};
            msg.reactions.forEach(r => {
                if(!reactionCounts[r.emoji]) reactionCounts[r.emoji] = {count:0, users:[]};
                reactionCounts[r.emoji].count++;
                reactionCounts[r.emoji].users.push(r.user_id);
            });
            for(let emoji in reactionCounts) {
                const hasReacted = reactionCounts[emoji].users.includes(CURRENT_USER_ID);
                reactionsHTML += `<span class="reaction-badge ${hasReacted ? 'user-reacted' : ''}" onclick="toggleReaction(${msg.id}, '${emoji}')">${emoji} ${reactionCounts[emoji].count}</span>`;
            }
        }
        reactionsHTML += '</div>';

        // Hover Actions
        let actionsHTML = `<div class="message-actions">`;
        if(!msg.is_deleted) {
            actionsHTML += `
                <button class="action-btn-sm" title="React" onclick="showReactionPicker(${msg.id})"><i class="bi bi-emoji-smile"></i></button>
                <button class="action-btn-sm" title="Reply" onclick="prepareReply(${msg.id}, '${escapeHTML(msg.sender_name)}', '${escapeHTML(msg.content)}')"><i class="bi bi-reply"></i></button>
                <button class="action-btn-sm" title="${msg.is_pinned ? 'Unpin' : 'Pin'}" onclick="togglePin(${msg.id})"><i class="bi bi-pin-angle"></i></button>
            `;
            if (isMe) {
                actionsHTML += `
                    <button class="action-btn-sm" title="Edit" onclick="prepareEdit(${msg.id}, '${escapeHTML(msg.content)}')"><i class="bi bi-pencil"></i></button>
                    <button class="action-btn-sm text-danger" title="Delete" onclick="deleteMessage(${msg.id})"><i class="bi bi-trash"></i></button>
                `;
            }
        }
        actionsHTML += `</div>`;

        return `
            <div class="message-row d-flex ${alignClass} mb-3 w-100 px-2 position-relative" id="msg-${msg.id}">
                ${!isMe ? `<div class="me-2 d-none d-md-block"><div class="avatar bg-secondary text-white rounded-circle d-flex align-items-center justify-content-center" style="width:30px; height:30px; font-size:0.8rem;">${msg.sender_name.charAt(0)}</div></div>` : ''}
                <div class="message-bubble ${bubbleClass} ${deletedClass} shadow-sm">
                    ${!isMe ? `<small class="fw-bold d-block mb-1" style="color:var(--bs-primary); font-size:0.75rem;">${msg.sender_name}</small>` : ''}
                    ${replyHTML}
                    ${fileHTML}
                    <div class="message-content">${contentHTML} ${editedTag}</div>
                    <div class="d-flex justify-content-end mt-1 align-items-center">
                        <small class="text-muted" style="font-size: 0.65rem;">${msg.timestamp.split(' ')[1]}</small>
                        ${isMe ? `<i class="bi bi-check2-all ms-1 text-primary" style="font-size: 0.7rem;"></i>` : ''}
                    </div>
                    ${reactionsHTML}
                </div>
                ${actionsHTML}
            </div>
        `;
    }

    /**
     * Handles the scrollToBottom functionality.
     */
    function scrollToBottom() {
        chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    }
    
    window.scrollToMessage = function(id) {
        const el = document.getElementById(`msg-${id}`);
        if(el) {
            el.scrollIntoView({behavior: 'smooth', block: 'center'});
            el.querySelector('.message-bubble').animate([
                { backgroundColor: '#fff3cd' },
                { backgroundColor: '' }
            ], { duration: 2000 });
        }
    }

    // --- Sending & Input Logic ---
    chatInputBox.addEventListener('input', () => {
        chatSendBtn.disabled = chatInputBox.value.trim().length === 0;
        
        // Typing Indicator logic
        if (!isTyping) {
            isTyping = true;
            socket.emit('typing', { type: activeChatTypeInput.value, id: activeChatIdInput.value });
        }
        clearTimeout(typingTimeout);
        typingTimeout = setTimeout(() => {
            isTyping = false;
            socket.emit('stop_typing', { type: activeChatTypeInput.value, id: activeChatIdInput.value });
        }, 2000);
    });

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const content = chatInputBox.value.trim();
        if (!content && !fileUploadInput.files.length) return;
        
        const type = activeChatTypeInput.value;
        const id = activeChatIdInput.value;
        const editId = editMessageIdInput.value;
        const replyId = replyToIdInput.value;
        const isAnnouncement = isAnnouncementInput.value === 'true';

        if (editId) {
            // Send Edit Request
            socket.emit('edit_message', { message_id: editId, new_content: content });
            cancelEditOrReply();
            return;
        }

        // Handle File Upload then Send Message
        if (fileUploadInput.files.length > 0) {
            const formData = new FormData();
            formData.append('file', fileUploadInput.files[0]);
            
            fetch('/chat/upload', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    if(data.file_url) {
                        sendMessageObj(type, id, content, data.file_url, replyId, isAnnouncement);
                        fileUploadInput.value = ''; // clear
                    }
                });
        } else {
            sendMessageObj(type, id, content, null, replyId, isAnnouncement);
        }
        
        cancelEditOrReply();
    });

    /**
     * Handles the sendMessageObj functionality.
     */
    function sendMessageObj(type, id, content, fileUrl, replyId, isAnnouncement) {
        socket.emit('send_message', {
            type: type,
            id: id,
            content: content,
            file_url: fileUrl,
            reply_to_id: replyId || null,
            is_announcement: isAnnouncement
        });
    }

    // --- Actions: Edit, Delete, Reply, Pin ---
    window.prepareEdit = function(id, content) {
        editMessageIdInput.value = id;
        chatInputBox.value = content;
        chatInputBox.focus();
        chatSendBtn.disabled = false;
        sendIcon.className = 'bi bi-check-lg fs-5'; // change icon to save
        chatInputBox.placeholder = "Edit message...";
    }

    window.deleteMessage = function(id) {
        if(confirm("Are you sure you want to delete this message?")) {
            socket.emit('delete_message', { message_id: id });
        }
    }

    window.prepareReply = function(id, name, content) {
        replyToIdInput.value = id;
        replyToName.textContent = name;
        replyToText.textContent = content;
        replyPreviewBar.classList.remove('d-none');
        chatInputBox.focus();
    }
    
    cancelReplyBtn.addEventListener('click', cancelEditOrReply);

    /**
     * Handles the cancelEditOrReply functionality.
     */
    function cancelEditOrReply() {
        editMessageIdInput.value = '';
        replyToIdInput.value = '';
        isAnnouncementInput.value = 'false';
        chatInputBox.value = '';
        chatInputBox.placeholder = "Type a message...";
        sendIcon.className = 'bi bi-send-fill fs-5';
        chatSendBtn.disabled = true;
        replyPreviewBar.classList.add('d-none');
    }

    window.togglePin = function(id) {
        socket.emit('pin_message', { message_id: id });
    }

    // --- Socket Event Listeners ---
    socket.on('receive_message', (msg) => {
        // If message belongs to active chat, render it
        if ((msg.chat_type === activeChatTypeInput.value && msg.chat_id == activeChatIdInput.value) || 
            (msg.chat_type === 'user' && msg.sender_id == activeChatIdInput.value)) {
            chatMessagesContainer.insertAdjacentHTML('beforeend', createMessageHTML(msg));
            scrollToBottom();
            
            // Send read receipt logic could go here
        } else {
            // Update unread badge in sidebar
            const selector = msg.chat_type === 'course' 
                ? `.group-item[data-chat-id="${msg.chat_id}"]` 
                : `.dm-item[data-chat-id="${msg.sender_id}"]`;
            const item = document.querySelector(selector);
            if(item) {
                const badge = item.querySelector('.unread-badge');
                badge.classList.remove('d-none');
                badge.textContent = parseInt(badge.textContent || 0) + 1;
                // move to top
                const container = msg.chat_type === 'course' ? document.querySelector('.group-header') : document.querySelector('.dm-header');
                container.after(item);
            }
        }
    });

    socket.on('message_edited', (data) => {
        if ((data.chat_type === activeChatTypeInput.value && data.chat_id == activeChatIdInput.value)) {
            const msgRow = document.getElementById(`msg-${data.message_id}`);
            if(msgRow) {
                const contentDiv = msgRow.querySelector('.message-content');
                contentDiv.innerHTML = `${escapeHTML(data.new_content)} <span class="msg-edited-tag">(edited)</span>`;
            }
        }
    });

    socket.on('message_deleted', (data) => {
        if ((data.chat_type === activeChatTypeInput.value && data.chat_id == activeChatIdInput.value)) {
            const msgRow = document.getElementById(`msg-${data.message_id}`);
            if(msgRow) {
                const bubble = msgRow.querySelector('.message-bubble');
                bubble.classList.add('msg-deleted');
                const contentDiv = bubble.querySelector('.message-content');
                contentDiv.innerHTML = "This message was deleted.";
                
                // hide attachments
                const attachment = bubble.querySelector('.attachment-preview, .file-card');
                if(attachment) attachment.remove();
                
                // hide actions
                const actions = msgRow.querySelector('.message-actions');
                if(actions) actions.remove();
            }
        }
    });

    socket.on('message_pinned', (data) => {
        if ((data.chat_type === activeChatTypeInput.value && data.chat_id == activeChatIdInput.value)) {
            // Reload history to ensure accurate pinned state, or just fetch pinned manually
            // For simplicity, we just reload history to ensure UI is completely accurate
            loadChatHistory(activeChatTypeInput.value, activeChatIdInput.value);
        }
    });

    socket.on('message_reacted', (data) => {
        if ((data.chat_type === activeChatTypeInput.value && data.chat_id == activeChatIdInput.value)) {
            // Realtime reaction update without full reload
            const msgRow = document.getElementById(`msg-${data.message_id}`);
            if(msgRow) {
                // To keep it simple and perfectly synced, fetching history is safe, but let's just trigger a soft reload
                // A soft reload ensures correct state
                loadChatHistory(activeChatTypeInput.value, activeChatIdInput.value);
            }
        }
    });

    socket.on('status_change', (data) => {
        const indicators = document.querySelectorAll(`.online-indicator[data-user-id="${data.user_id}"]`);
        indicators.forEach(ind => {
            if (data.status === 'online') {
                ind.classList.remove('d-none');
            } else {
                ind.classList.add('d-none');
            }
        });
        
        if (activeChatTypeInput.value === 'user' && activeChatIdInput.value == data.user_id) {
            chatSubtitle.innerHTML = data.status === 'online' 
                ? '<span class="status-dot bg-success d-inline-block rounded-circle me-1" style="width:8px; height:8px;"></span>Online'
                : '<span class="status-dot bg-secondary d-inline-block rounded-circle me-1" style="width:8px; height:8px;"></span>Offline';
        }
    });

    socket.on('user_typing', (data) => {
        if (activeChatTypeInput.value === data.chat_type && activeChatIdInput.value == data.chat_id) {
            const typingIndicator = document.querySelector(`.typing-indicator[data-user-id="${data.user_id}"]`);
            if(typingIndicator) typingIndicator.classList.remove('d-none');
            
            if(data.chat_type === 'course') {
                chatSubtitle.textContent = `${data.user_name} is typing...`;
            } else {
                chatSubtitle.textContent = "typing...";
            }
        }
    });

    socket.on('user_stop_typing', (data) => {
        if (activeChatTypeInput.value === data.chat_type && activeChatIdInput.value == data.chat_id) {
            const typingIndicator = document.querySelector(`.typing-indicator[data-user-id="${data.user_id}"]`);
            if(typingIndicator) typingIndicator.classList.add('d-none');
            
            if(data.chat_type === 'course') {
                chatSubtitle.textContent = "Group Chat";
            } else {
                chatSubtitle.innerHTML = '<span class="status-dot bg-success d-inline-block rounded-circle me-1" style="width:8px; height:8px;"></span>Online';
            }
        }
    });

    // --- Pinned Bar UI ---
    /**
     * Handles the updatePinnedBar functionality.
     */
    function updatePinnedBar() {
        if(currentPinnedMessages.length > 0) {
            const lastPin = currentPinnedMessages[currentPinnedMessages.length - 1];
            document.getElementById('pinnedMessageText').textContent = lastPin.content;
            pinnedMessagesBar.classList.remove('d-none');
            pinnedMessagesBar.classList.add('d-flex');
        } else {
            pinnedMessagesBar.classList.add('d-none');
            pinnedMessagesBar.classList.remove('d-flex');
        }
    }
    
    document.getElementById('closePinnedBar')?.addEventListener('click', () => {
        pinnedMessagesBar.classList.add('d-none');
        pinnedMessagesBar.classList.remove('d-flex');
    });


    // --- Emoji Picker ---
    emojiPickerBtn.addEventListener('click', () => {
        emojiPickerContainer.classList.toggle('d-none');
    });
    
    document.querySelector('emoji-picker').addEventListener('emoji-click', event => {
        chatInputBox.value += event.detail.unicode;
        chatSendBtn.disabled = false;
        emojiPickerContainer.classList.add('d-none');
        chatInputBox.focus();
    });
    
    // Close emoji picker on outside click
    document.addEventListener('click', (e) => {
        if(!emojiPickerContainer.contains(e.target) && !emojiPickerBtn.contains(e.target)) {
            emojiPickerContainer.classList.add('d-none');
        }
    });

    // --- Reactions Picker (Simplified) ---
    window.toggleReaction = function(msgId, emoji) {
        socket.emit('react_message', { message_id: msgId, emoji: emoji });
    }
    
    window.showReactionPicker = function(msgId) {
        const emojiList = ['👍', '❤️', '😂', '🎉', '👏', '🔥'];
        let pickerHtml = `<div class="position-absolute shadow bg-white rounded p-1 d-flex gap-1" style="bottom: 100%; z-index: 100; border: 1px solid #ddd; padding:5px;">`;
        emojiList.forEach(e => {
            pickerHtml += `<button class="btn btn-sm btn-light fs-5 p-1 px-2 border-0" onclick="toggleReaction(${msgId}, '${e}'); this.parentElement.remove();">${e}</button>`;
        });
        pickerHtml += `</div>`;
        
        const row = document.getElementById(`msg-${msgId}`);
        const actions = row.querySelector('.message-actions');
        if(actions) {
            actions.insertAdjacentHTML('afterbegin', pickerHtml);
        }
    }


    // --- Attachment Handling ---
    attachImageBtn.addEventListener('click', (e) => { e.preventDefault(); fileUploadInput.accept = "image/*,video/*"; fileUploadInput.click(); });
    attachDocumentBtn.addEventListener('click', (e) => { e.preventDefault(); fileUploadInput.accept = ".pdf,.doc,.docx,.ppt,.pptx,.zip"; fileUploadInput.click(); });
    
    if(toggleAnnouncementBtn) {
        toggleAnnouncementBtn.addEventListener('click', (e) => {
            e.preventDefault();
            isAnnouncementInput.value = 'true';
            chatInputBox.placeholder = "Type an announcement...";
            chatInputBox.focus();
        });
    }

    fileUploadInput.addEventListener('change', () => {
        if(fileUploadInput.files.length > 0) {
            chatInputBox.placeholder = `File attached: ${fileUploadInput.files[0].name}`;
            chatSendBtn.disabled = false;
        }
    });

    // --- Right Panel Toggle ---
    toggleInfoPanelBtn.addEventListener('click', () => {
        chatInfoPanel.classList.toggle('show');
        chatInfoPanel.classList.toggle('d-none');
        chatInfoPanel.classList.toggle('d-flex');
    });

    // --- Search & Filters ---
    toggleMessageSearch.addEventListener('click', () => {
        messageSearchBar.classList.toggle('d-none');
        if(!messageSearchBar.classList.contains('d-none')) messageSearchInput.focus();
    });
    
    closeMessageSearch.addEventListener('click', () => {
        messageSearchBar.classList.add('d-none');
        messageSearchInput.value = '';
        // reset highlighting here if implemented
    });

    globalChatSearch.addEventListener('input', (e) => {
        const val = e.target.value.toLowerCase();
        document.querySelectorAll('.chat-item').forEach(item => {
            const title = item.getAttribute('data-chat-title').toLowerCase();
            item.style.display = title.includes(val) ? 'flex' : 'none';
        });
    });

    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active', 'btn-primary'));
            filterBtns.forEach(b => b.classList.add('btn-outline-secondary'));
            btn.classList.add('active', 'btn-primary');
            btn.classList.remove('btn-outline-secondary');
            
            const filter = btn.getAttribute('data-filter');
            document.querySelectorAll('.filterable').forEach(item => {
                if(filter === 'all') { item.style.display = item.classList.contains('group-header') || item.classList.contains('dm-header') ? 'block' : 'flex'; }
                else if(filter === 'unread') {
                    if(item.classList.contains('chat-item')) {
                        const badge = item.querySelector('.unread-badge');
                        item.style.display = (badge && !badge.classList.contains('d-none')) ? 'flex' : 'none';
                    } else { item.style.display = 'none'; }
                }
                else if(filter === 'groups') {
                    item.style.display = (item.classList.contains('group-item') || item.classList.contains('group-header')) ? (item.classList.contains('group-header') ? 'block' : 'flex') : 'none';
                }
                else if(filter === 'dms') {
                    item.style.display = (item.classList.contains('dm-item') || item.classList.contains('dm-header')) ? (item.classList.contains('dm-header') ? 'block' : 'flex') : 'none';
                }
            });
        });
    });

    // Utility
    /**
     * Handles the escapeHTML functionality.
     */
    function escapeHTML(str) {
        if(!str) return '';
        return str.replace(/[&<>'"]/g, tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag]));
    }
});
