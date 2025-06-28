import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import EMSLocality, EMSChannel, EMSData

class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'dashboard_updates'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json['type']
        
        if message_type == 'request_update':
            locality_name = text_data_json['locality']
            data = await self.get_locality_data(locality_name)
            
            await self.send(text_data=json.dumps({
                'type': 'locality_update',
                'locality': locality_name,
                'data': data
            }))

    @database_sync_to_async
    def get_locality_data(self, locality_name):
        try:
            locality = EMSLocality.objects.get(loc_name=locality_name)
            channels = EMSChannel.objects.filter(locality=locality, is_active=True)
            
            data = []
            for channel in channels:
                latest_data = EMSData.objects.filter(
                    channel=channel,
                    interval='1'
                ).order_by('-timestamp').first()
                
                if latest_data:
                    data.append({
                        'channel_id': channel.channel_id,
                        'title': channel.title,
                        'value': latest_data.value,
                        'timestamp': latest_data.timestamp.isoformat(),
                        'unit': channel.unit
                    })
            
            return data
        except EMSLocality.DoesNotExist:
            return []

    # Called when a new data callback is received
    async def data_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_data',
            'locality': event['locality'],
            'data': event['data']
        }))