from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import EMSData

@receiver(post_save, sender=EMSData)
def notify_data_update(sender, instance, created, **kwargs):
    if created:  # Only for new data points
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'dashboard_updates',
            {
                'type': 'data_update',
                'locality': instance.channel.locality.loc_name,
                'data': {
                    'channel_id': instance.channel.channel_id,
                    'title': instance.channel.title,
                    'value': instance.value,
                    'timestamp': instance.timestamp.isoformat(),
                    'unit': instance.channel.unit
                }
            }
        )