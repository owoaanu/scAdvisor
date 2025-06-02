from django.db import models

class EMSLocality(models.Model):
    site = models.CharField(max_length=100)  # e.g., "ENS"
    loc_name = models.CharField(max_length=100)  # e.g., "Nihov"
    timezone = models.CharField(max_length=50)  # e.g., "01:00:00"
    last_verified = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('site', 'loc_name')
    
    def __str__(self):
        return f"{self.site}/{self.loc_name}"

class EMSChannel(models.Model):
    locality = models.ForeignKey(EMSLocality, on_delete=models.CASCADE)
    channel_id = models.IntegerField()
    title = models.CharField(max_length=200)
    default_title = models.CharField(max_length=200)
    range_group = models.CharField(max_length=100)
    
    class Meta:
        unique_together = ('locality', 'channel_id')
    
    def __str__(self):
        return f"Channel {self.channel_id}: {self.title}"

class EMSData(models.Model):
    channel = models.ForeignKey(EMSChannel, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    value = models.FloatField()
    interval = models.CharField(max_length=10)  # '2', '5', '10', '30', '60'
    
    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['interval']),
        ]
    
    def __str__(self):
        return f"{self.channel} at {self.timestamp}"