import json
from channels.generic.websocket import AsyncWebsocketConsumer

class CoinConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # all Pi connections and browser clients join the same group
        await self.channel_layer.group_add("coins", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("coins", self.channel_name)

    async def receive(self, text_data):
        """
        Called when the Pi (or any client) sends us data.
        We simply rebroadcast it to the "coins" group.
        """
        payload = json.loads(text_data)
        # You could do extra processing here (e.g. save to DB)

        # broadcast to all group members
        await self.channel_layer.group_send(
            "coins",
            {
                "type": "coin_message",
                "payload": payload
            }
        )

    async def coin_message(self, event):
        """
        Handler for messages sent to the "coins" group.
        Simply forward the payload to WebSocket.
        """
        await self.send(text_data=json.dumps(event["payload"]))
