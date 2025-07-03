"""
EMS Brno API Integration Utilities
Handles communication with EMS Brno API for fetching sensor data
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from .models import EMSLocality, EMSSensorData

logger = logging.getLogger(__name__)

class EMSAPIClient:
    """Client for interacting with EMS Brno API"""
    
    def __init__(self):
        self.base_url = "https://api.emsbrno.cz"
        self.session = requests.Session()
        
    def fetch_sensor_data(self, locality, days=1):
        """
        Fetch sensor data for a specific locality
        
        Args:
            locality: EMSLocality instance
            days: Number of days of data to fetch (default: 1)
            
        Returns:
            dict: Sensor data or None if error
        """
        try:
            # This would be called from the callback with auth tokens
            # For now, we'll simulate the data structure based on API docs
            
            # In real implementation, you would use the authenticated URLs
            # provided in the callback from EMS Brno
            
            logger.info(f"Fetching sensor data for {locality.loc_name}")
            
            # Simulate sensor data based on typical environmental monitoring
            # In real implementation, this would come from the API
            simulated_data = self._generate_simulated_data(locality)
            
            return simulated_data
            
        except Exception as e:
            logger.error(f"Error fetching sensor data for {locality.loc_name}: {e}")
            return None
    
    def _generate_simulated_data(self, locality):
        """
        Generate simulated sensor data for testing
        This will be replaced with actual API calls
        """
        import random
        
        # Base values for different locations
        base_values = {
            'Kikuletwa Kilimanjaro': {
                'temperature': 22.0,
                'humidity': 65.0,
                'pressure': 1013.25,
                'wind_speed': 3.5,
                'rainfall': 0.0
            },
            'Nasai Kati': {
                'temperature': 24.5,
                'humidity': 70.0,
                'pressure': 1012.8,
                'wind_speed': 2.8,
                'rainfall': 0.2
            },
            'Ngaroni Juu': {
                'temperature': 21.8,
                'humidity': 68.0,
                'pressure': 1014.1,
                'wind_speed': 4.2,
                'rainfall': 0.1
            }
        }
        
        base = base_values.get(locality.loc_name, base_values['Kikuletwa Kilimanjaro'])
        
        # Add some random variation
        return {
            'temperature': round(base['temperature'] + random.uniform(-2, 2), 1),
            'humidity': round(base['humidity'] + random.uniform(-5, 5), 1),
            'pressure': round(base['pressure'] + random.uniform(-2, 2), 2),
            'wind_speed': round(base['wind_speed'] + random.uniform(-1, 1), 1),
            'wind_direction': random.randint(0, 360),
            'rainfall': round(base['rainfall'] + random.uniform(0, 0.5), 2),
            'timestamp': timezone.now()
        }
    
    def process_data_callback(self, callback_data):
        """
        Process data callback from EMS Brno
        
        Args:
            callback_data: JSON data from EMS callback
            
        Returns:
            bool: Success status
        """
        try:
            site = callback_data.get('site')
            loc_name = callback_data.get('locName')
            time_zone = callback_data.get('timeZone')
            last_verified = callback_data.get('lastVerified')
            
            # Find the locality
            locality = EMSLocality.objects.get(
                site=site,
                loc_name=loc_name
            )
            
            # Update last verified time
            if last_verified:
                locality.last_verified = datetime.fromisoformat(last_verified.replace('Z', '+00:00'))
                locality.save()
            
            # Fetch and store sensor data
            sensor_data = self.fetch_sensor_data(locality)
            if sensor_data:
                self.store_sensor_data(locality, sensor_data)
                
            return True
            
        except EMSLocality.DoesNotExist:
            logger.error(f"Locality not found: {site}/{loc_name}")
            return False
        except Exception as e:
            logger.error(f"Error processing data callback: {e}")
            return False
    
    def store_sensor_data(self, locality, sensor_data):
        """
        Store sensor data in the database
        
        Args:
            locality: EMSLocality instance
            sensor_data: Dictionary containing sensor readings
        """
        try:
            # Create or update sensor data record
            sensor_record, created = EMSSensorData.objects.get_or_create(
                locality=locality,
                timestamp=sensor_data['timestamp'],
                defaults={
                    'temperature': sensor_data.get('temperature'),
                    'humidity': sensor_data.get('humidity'),
                    'pressure': sensor_data.get('pressure'),
                    'wind_speed': sensor_data.get('wind_speed'),
                    'wind_direction': sensor_data.get('wind_direction'),
                    'rainfall': sensor_data.get('rainfall'),
                }
            )
            
            if created:
                logger.info(f"Stored new sensor data for {locality.loc_name}")
            else:
                logger.info(f"Updated sensor data for {locality.loc_name}")
                
        except Exception as e:
            logger.error(f"Error storing sensor data: {e}")
    
    def fetch_chart_image(self, locality, channel_id, days=1):
        """
        Fetch chart image from EMS API
        
        Args:
            locality: EMSLocality instance
            channel_id: Channel identifier
            days: Number of days for chart
            
        Returns:
            bytes: Image data or None
        """
        try:
            # This would use the authenticated chart URLs from the callback
            # For now, return None as we don't have real auth tokens
            logger.info(f"Fetching chart for {locality.loc_name}, channel {channel_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching chart: {e}")
            return None

# Global instance
ems_client = EMSAPIClient()

