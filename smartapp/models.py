from django.db import models
from django.core.files.base import ContentFile
from django.utils import timezone
import json

class EMSLocality(models.Model):
    site = models.CharField(max_length=100)
    loc_name = models.CharField(max_length=100)
    timezone = models.CharField(max_length=50)
    last_verified = models.DateTimeField(null=True, blank=True)
    
    # Enhanced fields
    title = models.CharField(max_length=200, blank=True)  # Localized title
    original_url = models.URLField(blank=True)  # Original EMS URL
    is_active = models.BooleanField(default=True)
    last_callback_received = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('site', 'loc_name')
        verbose_name_plural = "EMS Localities"
    
    def __str__(self):
        return f"{self.site}/{self.loc_name}"

class EMSChannel(models.Model):
    locality = models.ForeignKey(EMSLocality, on_delete=models.CASCADE, related_name='channels')
    channel_id = models.IntegerField()
    title = models.CharField(max_length=200)
    default_title = models.CharField(max_length=200)
    range_group = models.CharField(max_length=100)
    
    # Enhanced fields
    unit = models.CharField(max_length=50, blank=True)  # Measurement unit
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    last_data_received = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('locality', 'channel_id')
        ordering = ['channel_id']
    
    def __str__(self):
        return f"Channel {self.channel_id}: {self.title}"

class EMSData(models.Model):
    channel = models.ForeignKey(EMSChannel, on_delete=models.CASCADE, related_name='data_points')
    timestamp = models.DateTimeField()
    value = models.FloatField()
    interval = models.CharField(max_length=10)
    
    # Enhanced fields
    quality_score = models.FloatField(default=1.0)  # Data quality indicator
    is_validated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['interval']),
            models.Index(fields=['channel', 'timestamp']),
        ]
        unique_together = ('channel', 'timestamp', 'interval')
    
    def __str__(self):
        return f"{self.channel} at {self.timestamp}: {self.value}"

class EMSImage(models.Model):
    locality = models.ForeignKey(EMSLocality, on_delete=models.CASCADE, related_name='images')
    channel = models.ForeignKey(EMSChannel, on_delete=models.CASCADE, related_name='images')
    interval = models.CharField(max_length=10)
    culture = models.CharField(max_length=10, default='en')
    image = models.ImageField(upload_to='ems_images/')
    
    # Enhanced fields
    width = models.IntegerField(default=600)
    height = models.IntegerField(default=400)
    file_size = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('locality', 'channel', 'interval', 'culture')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.locality} - Channel {self.channel} ({self.interval} days, {self.culture})"

class EMSCallbackLog(models.Model):
    """Log all callback requests for debugging and monitoring"""
    callback_type = models.CharField(max_length=20, choices=[
        ('data', 'Data Callback'),
        ('image', 'Image Callback')
    ])
    site = models.CharField(max_length=100)
    loc_name = models.CharField(max_length=100)
    payload = models.JSONField()
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    processing_time = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.callback_type} - {self.site}/{self.loc_name} at {self.created_at}"

# New sensor data models
class EMSSensorData(models.Model):
    """Model to store processed sensor readings from EMS devices"""
    
    locality = models.ForeignKey(EMSLocality, on_delete=models.CASCADE, related_name='sensor_data')
    timestamp = models.DateTimeField()
    
    # Environmental measurements
    temperature = models.FloatField(null=True, blank=True, help_text="Temperature in Celsius")
    humidity = models.FloatField(null=True, blank=True, help_text="Relative humidity in %")
    pressure = models.FloatField(null=True, blank=True, help_text="Atmospheric pressure in hPa")
    
    # Wind measurements
    wind_speed = models.FloatField(null=True, blank=True, help_text="Wind speed in m/s")
    wind_direction = models.FloatField(null=True, blank=True, help_text="Wind direction in degrees")
    
    # Precipitation
    rainfall = models.FloatField(null=True, blank=True, help_text="Rainfall in mm")
    
    # Additional measurements that might be available
    solar_radiation = models.FloatField(null=True, blank=True, help_text="Solar radiation in W/m²")
    soil_temperature = models.FloatField(null=True, blank=True, help_text="Soil temperature in Celsius")
    soil_moisture = models.FloatField(null=True, blank=True, help_text="Soil moisture in %")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-timestamp']
        unique_together = ['locality', 'timestamp']
        indexes = [
            models.Index(fields=['locality', '-timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.locality.loc_name} - {self.timestamp}"
    
    @property
    def temperature_fahrenheit(self):
        """Convert temperature to Fahrenheit"""
        if self.temperature is not None:
            return (self.temperature * 9/5) + 32
        return None
    
    @property
    def wind_speed_kmh(self):
        """Convert wind speed to km/h"""
        if self.wind_speed is not None:
            return self.wind_speed * 3.6
        return None