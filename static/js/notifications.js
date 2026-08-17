document.addEventListener('DOMContentLoaded', () => {
    // Check if socket is already defined globally, if not, create it
    const socket = window.socket || io();
    if (!window.socket) window.socket = socket;

    const notifBell = document.getElementById('notificationBell');
    const notifBadge = document.getElementById('notificationBadge');
    const notifDropdownList = document.getElementById('notificationDropdownList');
    
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }
    
    // Register Service Worker
    if ('serviceWorker' in navigator) {
        /**
         * Registers the service worker for background sync and push notifications.
         */
        navigator.serviceWorker.register('/sw.js').then(function(registration) {
            console.log('ServiceWorker registration successful with scope: ', registration.scope);
        }).catch(function(err) {
            console.log('ServiceWorker registration failed: ', err);
        });
    }

    // Request Desktop Notification Permission Custom Logic
    if ("Notification" in window) {
        if (Notification.permission === "default") {
            // Show custom prompt
            let promptHtml = `
            <div id="notificationPermissionModal" class="modal fade" tabindex="-1" role="dialog" data-bs-backdrop="static">
              <div class="modal-dialog modal-dialog-centered" role="document">
                <div class="modal-content border-0 shadow-lg rounded-4">
                  <div class="modal-body p-4 text-center">
                    <div class="mb-3 text-primary">
                        <i class="bi bi-bell-fill" style="font-size: 3rem;"></i>
                    </div>
                    <h5 class="fw-bold mb-3">AuraLearn wants to show notifications</h5>
                    <p class="text-muted mb-4">Enable notifications so you never miss important messages, announcements, or course updates.</p>
                    <div class="d-flex justify-content-center gap-3">
                        <button type="button" class="btn btn-outline-secondary px-4 rounded-pill" id="btnDenyNotif">Not Now</button>
                        <button type="button" class="btn btn-primary px-4 rounded-pill" id="btnAllowNotif">Allow Notifications</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>`;
            document.body.insertAdjacentHTML('beforeend', promptHtml);
            let notifModal = new bootstrap.Modal(document.getElementById('notificationPermissionModal'));
            notifModal.show();

            /**
             * Click event handler to allow notifications.
             * Requests browser permission and updates user preferences via API.
             */
            document.getElementById('btnAllowNotif').addEventListener('click', () => {
                Notification.requestPermission().then(permission => {
                    notifModal.hide();
                    if (permission === 'granted') {
                        document.body.dataset.notifDesktop = 'true';
                    }
                    /**
                     * API Request: Update notification preference to true.
                     */
                    fetch('/settings/update_notif_pref', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({desktop: permission === 'granted'})
                    });
                });
            });

            /**
             * Click event handler to deny notifications.
             * Updates user preferences via API to false.
             */
            document.getElementById('btnDenyNotif').addEventListener('click', () => {
                notifModal.hide();
                fetch('/settings/update_notif_pref', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({desktop: false})
                });
            });
        }
    }

    // Audio for notification sound
    const notifSound = new Audio('https://cdn.pixabay.com/download/audio/2021/08/04/audio_0625c1539c.mp3?filename=success-1-6297.mp3');
    
    /**
     * Socket.IO event handler for 'new_notification'.
     * Plays sound, shows desktop notification, updates UI badges, and displays a toast.
     */
    socket.on('new_notification', (data) => {
        console.log("RECEIVED NEW NOTIFICATION:", data);
        
        // 1. Play sound
        if (notifSound) {
            notifSound.play().catch(e => console.log('Audio play blocked:', e));
        }

        // 2. Desktop native notification
        console.log("Desktop notification check. window.Notification exists:", ("Notification" in window));
        if ("Notification" in window) {
            console.log("Current Notification.permission:", Notification.permission);
            if (Notification.permission === "granted") {
                const notifOptions = {
                    body: data.message,
                    icon: '/static/images/hero_img.jpg', // Add a placeholder icon just in case
                    requireInteraction: true
                };

                if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
                    console.log("Using Service Worker to show notification");
                    navigator.serviceWorker.ready.then(function(registration) {
                        notifOptions.data = { url: data.action_url };
                        registration.showNotification(data.title, notifOptions);
                    });
                } else {
                    console.log("Using standard Notification API");
                    let n = new Notification(data.title, notifOptions);
                    n.onclick = function() {
                        window.focus();
                        if (data.action_url) window.location.href = data.action_url;
                        this.close();
                    };
                }
            } else if (Notification.permission !== "denied") {
                console.log("Requesting Notification permission...");
                Notification.requestPermission().then(p => console.log("Permission requested, result:", p));
            } else {
                console.log("Notification permission is DENIED.");
            }
        }

        // 3. Show Toast (Real-Time Notification)
        showToast(data);

        // 4. Update Badge Count
        if (notifBadge) {
            let count = parseInt(notifBadge.innerText) || 0;
            count++;
            notifBadge.innerText = count;
            notifBadge.classList.remove('d-none');
            
            // Animate bell
            if (notifBell) {
                notifBell.classList.remove('bell-shake');
                void notifBell.offsetWidth; // Trigger reflow
                notifBell.classList.add('bell-shake');
            }
        }
        
        const sidebarBadge = document.getElementById('sidebarNotificationBadge');
        if (sidebarBadge) {
            let count = parseInt(sidebarBadge.innerText) || 0;
            count++;
            sidebarBadge.innerText = count;
            sidebarBadge.classList.remove('d-none');
        }

        // 5. Prepend to dropdown
        if (notifDropdownList) {
            const emptyMsg = notifDropdownList.querySelector('.empty-notifications');
            if (emptyMsg) emptyMsg.remove();

            const html = `
                <a href="/notifications/mark-read/${data.id}" class="notification-item unread notif-link" data-id="${data.id}" data-url="${data.action_url || '#'}">
                    <div class="notification-icon icon-${data.type}">
                        <i class="bi ${data.icon}"></i>
                    </div>
                    <div class="notification-content">
                        <div class="notification-title">${data.title}</div>
                        <div class="notification-message">${data.message}</div>
                        <div class="notification-time">Just now</div>
                    </div>
                </a>
            `;
            notifDropdownList.insertAdjacentHTML('afterbegin', html);
        }
    });

    /**
     * UI Update: Handles the showToast functionality to display real-time notifications.
     */
    function showToast(data) {
        const toastId = 'toast-' + data.id;
        const html = `
            <div id="${toastId}" class="toast glass-toast show" role="alert" aria-live="assertive" aria-atomic="true" data-bs-autohide="false">
                <div class="toast-header">
                    <i class="bi ${data.icon} text-${data.type} me-2"></i>
                    <strong class="me-auto">${data.title}</strong>
                    <small>Just now</small>
                    <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body" style="cursor: pointer;" onclick="window.location.href='/notifications/mark-read/${data.id}'">
                    ${data.message}
                </div>
            </div>
        `;
        toastContainer.insertAdjacentHTML('beforeend', html);
        
        const toastEl = document.getElementById(toastId);
        
        // Auto hide after 5 seconds
        setTimeout(() => {
            if(toastEl) {
                toastEl.classList.add('toast-fade-out');
                setTimeout(() => toastEl.remove(), 300);
            }
        }, 5000);
        
        // Handle close button
        const closeBtn = toastEl.querySelector('.btn-close');
        if(closeBtn) {
            closeBtn.addEventListener('click', () => {
                toastEl.classList.add('toast-fade-out');
                setTimeout(() => toastEl.remove(), 300);
            });
        }
    }

    /**
     * Click event listener for notification links via AJAX.
     * Marks the notification as read via API request and updates UI badges.
     */
    document.addEventListener('click', function(e) {
        const link = e.target.closest('.notif-link');
        if (link) {
            e.preventDefault();
            const id = link.dataset.id;
            const url = link.dataset.url;
            
            /**
             * API Request: Mark the specific notification as read.
             */
            fetch(`/notifications/mark-read/${id}`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            }).then(() => {
                link.classList.remove('unread');
                if (notifBadge) {
                    let count = parseInt(notifBadge.innerText) || 0;
                    if (count > 0) {
                        count--;
                        notifBadge.innerText = count;
                        if (count === 0) notifBadge.classList.add('d-none');
                    }
                }
                
                const sidebarBadge = document.getElementById('sidebarNotificationBadge');
                if (sidebarBadge) {
                    let count = parseInt(sidebarBadge.innerText) || 0;
                    if (count > 0) {
                        count--;
                        sidebarBadge.innerText = count;
                        if (count === 0) sidebarBadge.classList.add('d-none');
                    }
                }
                
                if (url && url !== '#' && url !== 'None') {
                    window.location.href = url;
                }
            });
        }
    });
});
