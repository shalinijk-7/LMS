self.addEventListener('notificationclick', function(event) {
    event.notification.close();

    const actionUrl = (event.notification.data && event.notification.data.url) ? event.notification.data.url : '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(windowClients => {
            // Check if there is already a window/tab open with the target URL
            for (let i = 0; i < windowClients.length; i++) {
                let client = windowClients[i];
                if (client.url.includes(actionUrl) && 'focus' in client) {
                    return client.focus();
                }
            }
            // If no window is open or it's a different URL, open a new one or focus an existing one and navigate
            if (windowClients.length > 0) {
                let client = windowClients[0];
                return client.focus().then(c => c.navigate(actionUrl));
            } else if (clients.openWindow) {
                return clients.openWindow(actionUrl);
            }
        })
    );
});

self.addEventListener('install', function(event) {
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    event.waitUntil(clients.claim());
});
