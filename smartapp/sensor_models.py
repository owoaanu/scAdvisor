"""
Enhanced sensor data models for EMS integration
"""

from django.db import models
from django.utils import timezone
from .models import EMSLocality

class EMSSensorData(models.Model):
    """Model to store sensor readings from EMS devices"""
    
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

class EMSChannel(models.Model):
    """Model to store EMS channel information"""
    
    locality = models.ForeignKey(EMSLocality, on_delete=models.CASCADE, related_name='channels')
    channel_id = models.CharField(max_length=50)
    channel_name = models.CharField(max_length=200)
    unit = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    
    # Channel metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['locality', 'channel_id']
        indexes = [
            models.Index(fields=['locality', 'channel_id']),
        ]
    
    def __str__(self):
        return f"{self.locality.loc_name} - {self.channel_name}"

class EMSImage(models.Model):
    """Model to store EMS chart images"""
    
    locality = models.ForeignKey(EMSLocality, on_delete=models.CASCADE, related_name='images')
    channel = models.ForeignKey(EMSChannel, on_delete=models.CASCADE, null=True, blank=True)
    
    # Image metadata
    image_type = models.CharField(max_length=50, default='chart')
    time_period = models.CharField(max_length=20)  # e.g., '1', '2', '5', '10', '30', '60' days
    
    # Image data
    image_data = models.BinaryField()
    content_type = models.CharField(max_length=50, default='image/png')
    filename = models.CharField(max_length=200)
    
    # Timestamps
    generated_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['locality', '-generated_at']),
            models.Index(fields=['locality', 'time_period']),
        ]
    
    def __str__(self):
        return f"{self.locality.loc_name} - {self.image_type} ({self.time_period})"

class EMSDataLog(models.Model):
    """Model to log API interactions and data updates"""
    
    locality = models.ForeignKey(EMSLocality, on_delete=models.CASCADE, related_name='data_logs')
    
    # Log details
    log_type = models.CharField(max_length=50)  # 'data_callback', 'image_callback', 'api_call'
    status = models.CharField(max_length=20)    # 'success', 'error', 'warning'
    message = models.TextField()
    
    # Request/response data
    request_data = models.JSONField(null=True, blank=True)
    response_data = models.JSONField(null=True, blank=True)
    
    # Timing
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['locality', '-timestamp']),
            models.Index(fields=['log_type', '-timestamp']),
            models.Index(fields=['status', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.locality.loc_name} - {self.log_type} ({self.status})"

