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
        data = json.loads(text_data)
        event = data.get("event")

        # Pi → broadcast coin_inserted
        if event == "coin_inserted":
            await self.channel_layer.group_send(
                self.GROUP_NAME,
                {
                    "type": "coin_inserted",    # maps to method coin_inserted()
                    "coin_count": data["coin_count"],
                }
            )

        # Browser → broadcast reset_coins
        elif event == "reset_coins":
            await self.channel_layer.group_send(
                self.GROUP_NAME,
                {
                    "type": "coin_reset"       # maps to method coin_reset()
                }
            )

    async def coin_message(self, event):
        """
        Handler for messages sent to the "coins" group.
        Simply forward the payload to WebSocket.
        """
        await self.send(text_data=json.dumps(event["payload"]))

    # Handler for Pi/browser to consume coin_inserted events
    async def coin_inserted(self, event):
        await self.send(text_data=json.dumps({
            "event": "coin_inserted",
            "coin_count": event["coin_count"],
        }))

    # Handler for Pi/browser to consume reset_coins events
    async def coin_reset(self, event):
        await self.send(text_data=json.dumps({
            "event": "reset_coins"
        }))
