self.addEventListener('push', function (event) {
  var body = 'Someone replied to your question on A Kinder Place.';
  try { if (event.data) body = event.data.text(); } catch (e) {}
  event.waitUntil(
    self.registration.showNotification('A Kinder Place', {
      body: body,
      icon: '/static/style.css'
    })
  );
});
self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  event.waitUntil(clients.openWindow('/'));
});
