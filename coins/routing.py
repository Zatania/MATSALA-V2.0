from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Matches ws(s)://<host>/ws/coins/
    re_path(r"^ws/coins/$", consumers.CoinConsumer.as_asgi()),
]
