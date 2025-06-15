import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
import coins.routing     # we’ll create this next

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    # HTTP → your existing Django views
    "http": django_asgi_app,

    # WebSocket → our consumer
    "websocket": URLRouter(
        coins.routing.websocket_urlpatterns
    ),
})
