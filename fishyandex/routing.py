from django.urls import path
from authentication.views import CleanupInactiveDriversConsumer

websocket_urlpatterns = [
    path('ws/cleanup_inactive_drivers/', CleanupInactiveDriversConsumer.as_asgi()),
]