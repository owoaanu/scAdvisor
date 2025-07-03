"""
EMS Image Callback Handler

This module handles image callbacks from the EMS Brno API system.
It processes incoming image data and stores it for dashboard display.
"""

import os
import json
import logging
import requests
from datetime import datetime, timezone
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone as django_timezone
from .models import EMSLocality, EMSChannel, EMSImage, EMSCallbackLog

logger = logging.getLogger(__name__)

class EMSImageCallbackHandler:
    """Handles EMS image callback processing"""
    
    def __init__(self):
        self.supported_formats = ['png', 'jpg', 'jpeg', 'gif', 'svg']
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        
    def process_callback(self, request):
        """
        Process incoming image callback from EMS API
        
        Expected callback format based on PHP example:
        - locName: Location name
        - channelId: Channel identifier
        - interval: Time interval (1, 5, 10 days)
        - culture: Language/culture code
        - image data: Binary image content
        """
        try:
            # Log the callback
            callback_log = EMSCallbackLog.objects.create(
                callback_type='image',
                raw_data=self._get_request_summary(request),
                ip_address=self._get_client_ip(request)
            )
            
            # Extract parameters
            loc_name = request.POST.get('locName') or request.GET.get('locName')
            channel_id = request.POST.get('channelId') or request.GET.get('channelId')
            interval = request.POST.get('interval', '1')
            culture = request.POST.get('culture', 'en')
            
            if not loc_name or not channel_id:
                error_msg = "Missing required parameters: locName and channelId"
                logger.error(error_msg)
                callback_log.error_message = error_msg
                callback_log.save()
                return JsonResponse({'error': error_msg}, status=400)
            
            # Find the locality
            try:
                locality = EMSLocality.objects.get(loc_name=loc_name)
            except EMSLocality.DoesNotExist:
                error_msg = f"Locality not found: {loc_name}"
                logger.error(error_msg)
                callback_log.error_message = error_msg
                callback_log.save()
                return JsonResponse({'error': error_msg}, status=404)
            
            # Find or create the channel
            channel, created = EMSChannel.objects.get_or_create(
                locality=locality,
                channel_id=channel_id,
                defaults={
                    'title': f'Channel {channel_id}',
                    'unit': '',
                    'is_active': True
                }
            )
            
            if created:
                logger.info(f"Created new channel: {channel_id} for {loc_name}")
            
            # Process image data
            image_data = None
            content_type = request.content_type
            
            if 'multipart/form-data' in content_type:
                # Handle multipart form data
                if 'image' in request.FILES:
                    image_file = request.FILES['image']
                    image_data = image_file.read()
                    content_type = image_file.content_type
            elif 'image/' in content_type:
                # Handle direct image upload
                image_data = request.body
            else:
                # Try to get image from POST data
                image_url = request.POST.get('imageUrl')
                if image_url:
                    image_data = self._download_image(image_url)
                    content_type = 'image/png'  # Default
            
            if not image_data:
                error_msg = "No image data found in request"
                logger.error(error_msg)
                callback_log.error_message = error_msg
                callback_log.save()
                return JsonResponse({'error': error_msg}, status=400)
            
            # Validate image size
            if len(image_data) > self.max_file_size:
                error_msg = f"Image too large: {len(image_data)} bytes"
                logger.error(error_msg)
                callback_log.error_message = error_msg
                callback_log.save()
                return JsonResponse({'error': error_msg}, status=413)
            
            # Determine file extension
            file_ext = self._get_file_extension(content_type)
            if not file_ext:
                file_ext = 'png'  # Default
            
            # Generate filename
            timestamp = django_timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{loc_name}_{channel_id}_{interval}d_{culture}_{timestamp}.{file_ext}"
            
            # Save the image
            image_file = ContentFile(image_data, name=filename)
            
            # Create or update EMSImage record
            ems_image, created = EMSImage.objects.update_or_create(
                locality=locality,
                channel=channel,
                interval=interval,
                culture=culture,
                defaults={
                    'image': image_file,
                    'file_size': len(image_data),
                    'content_type': content_type,
                    'created_at': django_timezone.now()
                }
            )
            
            # Update locality last callback time
            locality.last_callback_received = django_timezone.now()
            locality.save()
            
            # Update callback log
            callback_log.processed_successfully = True
            callback_log.locality = locality
            callback_log.save()
            
            logger.info(f"Successfully processed image callback for {loc_name}/{channel_id}")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Image processed successfully',
                'image_id': ems_image.id,
                'filename': filename
            })
            
        except Exception as e:
            error_msg = f"Error processing image callback: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            if 'callback_log' in locals():
                callback_log.error_message = error_msg
                callback_log.save()
            
            return JsonResponse({'error': error_msg}, status=500)
    
    def _download_image(self, url):
        """Download image from URL"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            return None
    
    def _get_file_extension(self, content_type):
        """Get file extension from content type"""
        content_type_map = {
            'image/png': 'png',
            'image/jpeg': 'jpg',
            'image/jpg': 'jpg',
            'image/gif': 'gif',
            'image/svg+xml': 'svg'
        }
        return content_type_map.get(content_type.lower())
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _get_request_summary(self, request):
        """Get a summary of the request for logging"""
        return {
            'method': request.method,
            'path': request.path,
            'content_type': request.content_type,
            'content_length': len(request.body) if request.body else 0,
            'get_params': dict(request.GET),
            'post_params': {k: v for k, v in request.POST.items() if k != 'image'},
            'files': list(request.FILES.keys()) if hasattr(request, 'FILES') else []
        }

# Initialize handler instance
image_callback_handler = EMSImageCallbackHandler()

@csrf_exempt
@require_http_methods(["GET", "POST"])
def ems_image_callback_view(request):
    """
    Django view for handling EMS image callbacks
    
    This endpoint receives image data from the EMS Brno API system
    and stores it for display in the dashboard.
    
    URL: /ems-image-callback/
    Methods: GET, POST
    
    Parameters:
    - locName: Location name (required)
    - channelId: Channel identifier (required)  
    - interval: Time interval in days (default: 1)
    - culture: Language code (default: en)
    - image: Image file or image data
    """
    return image_callback_handler.process_callback(request)

def generate_test_image_callback(locality_name, channel_id='1', interval='1'):
    """
    Generate a test image callback for development/testing
    
    This function creates a simple test chart image and processes it
    as if it came from the EMS API callback.
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        from io import BytesIO
        
        # Create a simple test chart
        fig, ax = plt.subplots(figsize=(8, 6))
        
        # Generate sample data
        x = np.linspace(0, 24, 100)
        y = 20 + 5 * np.sin(x/4) + np.random.normal(0, 0.5, 100)
        
        ax.plot(x, y, 'b-', linewidth=2)
        ax.set_xlabel('Time (hours)')
        ax.set_ylabel('Temperature (°C)')
        ax.set_title(f'Temperature Data - {locality_name}')
        ax.grid(True, alpha=0.3)
        
        # Save to bytes
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_data = buffer.getvalue()
        plt.close()
        
        # Find the locality
        locality = EMSLocality.objects.get(loc_name=locality_name)
        
        # Find or create channel
        channel, created = EMSChannel.objects.get_or_create(
            locality=locality,
            channel_id=channel_id,
            defaults={
                'title': 'Temperature',
                'unit': '°C',
                'is_active': True
            }
        )
        
        # Generate filename
        timestamp = django_timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{locality_name}_{channel_id}_{interval}d_en_{timestamp}.png"
        
        # Save the image
        image_file = ContentFile(image_data, name=filename)
        
        # Create EMSImage record
        ems_image, created = EMSImage.objects.update_or_create(
            locality=locality,
            channel=channel,
            interval=interval,
            culture='en',
            defaults={
                'image': image_file,
                'file_size': len(image_data),
                'content_type': 'image/png',
                'created_at': django_timezone.now()
            }
        )
        
        logger.info(f"Generated test image for {locality_name}/{channel_id}")
        return ems_image
        
    except Exception as e:
        logger.error(f"Failed to generate test image: {e}")
        return None

