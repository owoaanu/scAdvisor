import os
from django.shortcuts import render, redirect, HttpResponse
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
# from django.templatetags.static import static
from django.conf import settings
import json

import requests
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import EMSLocality, EMSChannel, EMSData, EMSImage  # Add EMSImage
from django.core.files.base import ContentFile
from datetime import datetime
import logging

logger = logging.getLogger(__name__)



# Create your views here.
def index(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')
  
  
def services(request):
    return render(request, 'services.html')
    
def projects(request):
    return render(request, 'projects.html')
   
def contact(request):
    return render(request, 'contact.html')
    
    
def signup(request):
    form = UserCreationForm()
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('signin')
    return render(request, 'signup.html', {"form":form})
    

def signin(request):
    if request.method == 'POST':
            username = request.POST.get("username")
            password = request.POST.get("password")
            user = authenticate(request, username=username,password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'welcome {username}')
                return redirect('index')
            else:
                messages.info(request, f'Accounts do not exist please signin!') 
                return redirect('signin')
    form =  AuthenticationForm()
    return render(request, 'signin.html', {"form":form})



def signout(request):
    logout(request)
    return redirect('/')


#====================================================================
#====================================================================
#====================================================================

import requests
import json
import time
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime
from .models import EMSLocality, EMSChannel, EMSData, EMSCallbackLog
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def ems_data_callback(request):
    start_time = time.time()
    callback_log = None
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)
    
    try:
        # Parse request body
        if not request.body:
            return JsonResponse({'error': 'Empty request body'}, status=400)
            
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError as e:
            return JsonResponse({'error': f'Invalid JSON: {str(e)}'}, status=400)
        
        # Create callback log entry
        callback_log = EMSCallbackLog.objects.create(
            callback_type='data',
            site=data.get('site', ''),
            loc_name=data.get('locName', ''),
            payload=data
        )
        
        # Validate required fields
        required_fields = ['site', 'locName', 'timeZone', 'channels', 'data']
        for field in required_fields:
            if field not in data:
                error_msg = f'Missing required field: {field}'
                callback_log.error_message = error_msg
                callback_log.save()
                return JsonResponse({'error': error_msg}, status=400)
        
        # Extract data
        site = data['site']
        loc_name = data['locName']
        timezone_str = data['timeZone']
        channels_url = data['channels']
        data_intervals = data['data']
        last_verified = data.get('lastVerified')
        
        # Fetch channel information with enhanced error handling
        try:
            channels_response = requests.get(f"{channels_url}&inclLocality=true", timeout=30)
            channels_response.raise_for_status()
            channels_data = channels_response.json()
        except requests.exceptions.RequestException as e:
            error_msg = f'Failed to fetch channels: {str(e)}'
            callback_log.error_message = error_msg
            callback_log.save()
            return JsonResponse({'error': error_msg}, status=400)
        
        # Create/update locality with enhanced information
        locality_info = channels_data.get('localities', {}).get(site, {}).get(loc_name, {})
        locality, created = EMSLocality.objects.update_or_create(
            site=site,
            loc_name=loc_name,
            defaults={
                'timezone': timezone_str,
                'last_verified': datetime.fromisoformat(last_verified) if last_verified else None,
                'title': locality_info.get('title', loc_name),
                'original_url': locality_info.get('url', ''),
                'last_callback_received': timezone.now()
            }
        )
        
        # Process channels with enhanced metadata
        channels_processed = 0
        for channel_id, channel_info in channels_data.get('channels', {}).items():
            channel, created = EMSChannel.objects.update_or_create(
                locality=locality,
                channel_id=int(channel_id),
                defaults={
                    'title': channel_info.get('title', ''),
                    'default_title': channel_info.get('defaultTitle', channel_info.get('title', '')),
                    'range_group': channel_info.get('rangeGroup', ''),
                    'unit': channel_info.get('unit', ''),
                    'description': channel_info.get('description', ''),
                    'last_data_received': timezone.now()
                }
            )
            channels_processed += 1
        
        # Process actual sensor data for each interval
        data_points_processed = 0
        for interval, interval_data in data_intervals.items():
            data_url = interval_data.get('url')
            if not data_url:
                continue
                
            try:
                # Fetch actual sensor data
                data_response = requests.get(data_url, timeout=60)
                data_response.raise_for_status()
                sensor_data = data_response.json()
                
                # Process each channel's data
                for channel_id, channel_data in sensor_data.get('channels', {}).items():
                    try:
                        channel = EMSChannel.objects.get(
                            locality=locality,
                            channel_id=int(channel_id)
                        )
                        
                        # Process data points
                        for data_point in channel_data.get('data', []):
                            timestamp_str = data_point.get('time')
                            value = data_point.get('value')
                            
                            if timestamp_str and value is not None:
                                # Parse timestamp (adjust format as needed)
                                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                
                                # Create or update data point
                                data_obj, created = EMSData.objects.update_or_create(
                                    channel=channel,
                                    timestamp=timestamp,
                                    interval=interval,
                                    defaults={
                                        'value': float(value),
                                        'quality_score': data_point.get('quality', 1.0),
                                        'is_validated': True
                                    }
                                )
                                
                                if created:
                                    data_points_processed += 1
                                    
                    except EMSChannel.DoesNotExist:
                        logger.warning(f"Channel {channel_id} not found for locality {locality}")
                        continue
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid data point for channel {channel_id}: {str(e)}")
                        continue
                        
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch data for interval {interval}: {str(e)}")
                continue
        
        # Update callback log with success
        processing_time = time.time() - start_time
        callback_log.success = True
        callback_log.processing_time = processing_time
        callback_log.save()
        
        logger.info(f"Data callback processed successfully: {channels_processed} channels, {data_points_processed} data points in {processing_time:.2f}s")
        
        return JsonResponse({
            'status': 'success',
            'channels_processed': channels_processed,
            'data_points_processed': data_points_processed,
            'processing_time': processing_time
        })
    
    except Exception as e:
        error_msg = f'Processing error: {str(e)}'
        logger.error(error_msg, exc_info=True)
        
        if callback_log:
            callback_log.error_message = error_msg
            callback_log.processing_time = time.time() - start_time
            callback_log.save()
        
        return JsonResponse({'error': error_msg}, status=500)
    
    
    
    

@csrf_exempt
def ems_image_callback(request):
    start_time = time.time()
    callback_log = None
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)
    
    try:
        # Parse request body
        if not request.body:
            return JsonResponse({'error': 'Empty request body'}, status=400)
            
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError as e:
            return JsonResponse({'error': f'Invalid JSON: {str(e)}'}, status=400)
        
        # Create callback log entry
        callback_log = EMSCallbackLog.objects.create(
            callback_type='image',
            site=data.get('site', ''),
            loc_name=data.get('locName', ''),
            payload=data
        )
        
        # Validate required fields
        required_fields = ['site', 'locName', 'cultures']
        for field in required_fields:
            if field not in data:
                error_msg = f'Missing required field: {field}'
                callback_log.error_message = error_msg
                callback_log.save()
                return JsonResponse({'error': error_msg}, status=400)
        
        site = data['site']
        loc_name = data['locName']
        cultures = data['cultures']
        
        try:
            locality = EMSLocality.objects.get(site=site, loc_name=loc_name)
        except EMSLocality.DoesNotExist:
            error_msg = 'Locality not found'
            callback_log.error_message = error_msg
            callback_log.save()
            return JsonResponse({'error': error_msg}, status=404)
        
        images_processed = 0
        
        # Process each culture (language)
        for culture, culture_data in cultures.items():
            # Get channel metadata using the shortest interval (following PHP example)
            try:
                channels_url = culture_data['channels']['1']['url']
                channels_response = requests.get(f"{channels_url}&inclLocality=true", timeout=30)
                channels_response.raise_for_status()
                channels_data = channels_response.json()
            except Exception as e:
                logger.warning(f"Failed to get channels for culture {culture}: {str(e)}")
                continue
            
            # Process specific intervals (following PHP example: 1, 5, 10 days)
            for interval in ['1', '5', '10']:
                if interval not in culture_data.get('chart', {}):
                    continue
                
                for channel_id, chart_info in culture_data['chart'][interval].items():
                    try:
                        # Get channel object
                        channel = EMSChannel.objects.get(
                            locality=locality,
                            channel_id=int(channel_id)
                        )
                        
                        # Download chart image with custom dimensions (from PHP example)
                        chart_url = f"{chart_info['url']}&width=800&height=500"
                        img_response = requests.get(chart_url, timeout=60)
                        img_response.raise_for_status()
                        
                        # Create filename following PHP example convention
                        img_name = f"chart_{channel_id}_{interval}_{culture}.png"
                        
                        # Save or update image
                        ems_image, created = EMSImage.objects.update_or_create(
                            locality=locality,
                            channel=channel,
                            interval=interval,
                            culture=culture,
                            defaults={
                                'image': ContentFile(img_response.content, name=img_name),
                                'width': 800,
                                'height': 500,
                                'file_size': len(img_response.content)
                            }
                        )
                        
                        images_processed += 1
                        logger.debug(f"Processed image for channel {channel_id}, interval {interval}, culture {culture}")
                        
                    except EMSChannel.DoesNotExist:
                        logger.warning(f"Channel {channel_id} not found for locality {locality}")
                        continue
                    except requests.exceptions.RequestException as e:
                        logger.warning(f"Failed to download image for channel {channel_id}: {str(e)}")
                        continue
                    except Exception as e:
                        logger.warning(f"Error processing image for channel {channel_id}: {str(e)}")
                        continue
        
        # Update callback log with success
        processing_time = time.time() - start_time
        callback_log.success = True
        callback_log.processing_time = processing_time
        callback_log.save()
        
        logger.info(f"Image callback processed successfully: {images_processed} images in {processing_time:.2f}s")
        
        return JsonResponse({
            'status': 'success',
            'images_processed': images_processed,
            'processing_time': processing_time
        })
    
    except Exception as e:
        error_msg = f'Processing error: {str(e)}'
        logger.error(error_msg, exc_info=True)
        
        if callback_log:
            callback_log.error_message = error_msg
            callback_log.processing_time = time.time() - start_time
            callback_log.save()
        
        return JsonResponse({'error': error_msg}, status=500)
    
    



### Additional API Endpoints for Dashboard

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

@login_required
@require_http_methods(["GET"])
def api_locality_data(request, loc_name):
    """API endpoint to get latest data for a specific locality"""
    try:
        locality = get_object_or_404(EMSLocality, loc_name=loc_name)
        channels = EMSChannel.objects.filter(locality=locality, is_active=True)
        
        data = {
            'locality': {
                'site': locality.site,
                'loc_name': locality.loc_name,
                'title': locality.title,
                'timezone': locality.timezone,
                'last_callback_received': locality.last_callback_received.isoformat() if locality.last_callback_received else None
            },
            'channels': []
        }
        
        for channel in channels:
            # Get latest data point for each interval
            latest_data = {}
            for interval in ['1', '5', '10']:
                latest_point = EMSData.objects.filter(
                    channel=channel,
                    interval=interval
                ).order_by('-timestamp').first()
                
                if latest_point:
                    latest_data[interval] = {
                        'timestamp': latest_point.timestamp.isoformat(),
                        'value': latest_point.value,
                        'quality_score': latest_point.quality_score
                    }
            
            data['channels'].append({
                'channel_id': channel.channel_id,
                'title': channel.title,
                'unit': channel.unit,
                'range_group': channel.range_group,
                'latest_data': latest_data
            })
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_locality_images(request, loc_name):
    """API endpoint to get latest images for a specific locality"""
    try:
        locality = get_object_or_404(EMSLocality, loc_name=loc_name)
        interval = request.GET.get('interval', '1')
        culture = request.GET.get('culture', 'en')
        
        images = EMSImage.objects.filter(
            locality=locality,
            interval=interval,
            culture=culture
        ).select_related('channel').order_by('channel__channel_id')
        
        data = {
            'locality': locality.loc_name,
            'interval': interval,
            'culture': culture,
            'images': []
        }
        
        for image in images:
            data['images'].append({
                'channel_id': image.channel.channel_id,
                'channel_title': image.channel.title,
                'image_url': image.image.url,
                'width': image.width,
                'height': image.height,
                'created_at': image.created_at.isoformat()
            })
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
    


@login_required
def dashboard(request):
    """Enhanced dashboard with real sensor data"""
    from .api_utils import ems_client
    from .models import EMSSensorData
    from datetime import timedelta
    
    # Get all active localities
    device_locations = EMSLocality.objects.filter(is_active=True).order_by('loc_name')
    
    # Get selected parameters
    selected_locality = request.GET.get('locality')
    interval = request.GET.get('interval', '1')  # Default to 1 day
    
    dashboard_data = []
    
    for locality in device_locations:
        # Get latest sensor data
        latest_sensor_data = EMSSensorData.objects.filter(
            locality=locality
        ).order_by('-timestamp').first()
        
        # If no sensor data exists, generate some simulated data
        if not latest_sensor_data:
            try:
                sensor_data = ems_client.fetch_sensor_data(locality)
                if sensor_data:
                    ems_client.store_sensor_data(locality, sensor_data)
                    latest_sensor_data = EMSSensorData.objects.filter(
                        locality=locality
                    ).order_by('-timestamp').first()
            except Exception as e:
                logger.warning(f"Failed to generate sensor data for {locality.loc_name}: {e}")
        
        # Get channel data
        channels = EMSChannel.objects.filter(
            locality=locality,
            is_active=True
        ).order_by('channel_id')
        
        channel_data = []
        for channel in channels:
            # Get latest data point
            latest_data = EMSData.objects.filter(
                channel=channel,
                interval=interval
            ).order_by('-timestamp').first()
            
            channel_info = {
                'channel': channel,
                'latest_data': latest_data,
                'has_recent_data': latest_data and (
                    timezone.now() - latest_data.timestamp
                ).total_seconds() < 86400  # Within 24 hours
            }
            channel_data.append(channel_info)
        
        # Get images for this locality
        images = EMSImage.objects.filter(
            locality=locality,
            interval=interval,
            culture='en'
        ).select_related('channel').order_by('channel__channel_id')
        
        # Calculate data freshness
        data_freshness = 'unknown'
        if latest_sensor_data:
            time_diff = timezone.now() - latest_sensor_data.timestamp
            if time_diff.total_seconds() < 3600:  # 1 hour
                data_freshness = 'fresh'
            elif time_diff.total_seconds() < 86400:  # 24 hours
                data_freshness = 'recent'
            else:
                data_freshness = 'stale'
        
        locality_data = {
            'locality': locality,
            'latest_sensor_data': latest_sensor_data,
            'channels': channel_data,
            'images': images,
            'data_freshness': data_freshness,
            'last_update': locality.last_callback_received,
            'has_sensor_data': latest_sensor_data is not None
        }
        
        dashboard_data.append(locality_data)
    
    # Get recent callback logs for monitoring
    recent_logs = EMSCallbackLog.objects.order_by('-created_at')[:10]
    
    # Calculate system statistics
    total_localities = device_locations.count()
    active_localities = device_locations.filter(
        last_callback_received__gte=timezone.now() - timedelta(hours=24)
    ).count()
    
    context = {
        'dashboard_data': dashboard_data,
        'device_locations': [loc.loc_name for loc in device_locations],
        'selected_locality': selected_locality,
        'selected_interval': interval,
        'available_intervals': [
            ('1', '1 Day'),
            ('5', '5 Days'),
            ('10', '10 Days')
        ],
        'recent_logs': recent_logs,
        'total_localities': total_localities,
        'active_localities': active_localities
    }
    
    return render(request, 'dashboard.html', context)




# Security middleware for EMS callbacks
from django.http import HttpResponseForbidden
from django.conf import settings
import ipaddress

class EMSCallbackSecurityMiddleware:
    """Middleware to secure EMS API callbacks"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Define allowed IP ranges for EMS callbacks
        self.allowed_networks = [
            ipaddress.ip_network('0.0.0.0/0'),  # Allow all for now - restrict as needed
        ]

    def __call__(self, request):
        # Check if this is an EMS callback endpoint
        if request.path in ['/ems-callback/', '/ems-image-callback/']:
            if not self.is_allowed_ip(request):
                return HttpResponseForbidden('Access denied')
            
            # Add rate limiting here if needed
            if not self.check_rate_limit(request):
                return HttpResponseForbidden('Rate limit exceeded')
        
        response = self.get_response(request)
        return response

    def is_allowed_ip(self, request):
        """Check if the request IP is from an allowed network"""
        client_ip = self.get_client_ip(request)
        if not client_ip:
            return False
        
        try:
            client_ip_obj = ipaddress.ip_address(client_ip)
            return any(client_ip_obj in network for network in self.allowed_networks)
        except ValueError:
            return False

    def get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def check_rate_limit(self, request):
        """Implement rate limiting for callbacks"""
        # Simple rate limiting - implement more sophisticated logic as needed
        return True



### Data Validation and Sanitization

from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
import re

class EMSDataValidator:
    """Validator for EMS API data"""
    
    @staticmethod
    def validate_sensor_value(value, channel):
        """Validate sensor values based on channel type"""
        try:
            numeric_value = float(value)
            
            # Define reasonable ranges for different sensor types
            ranges = {
                'temperature': (-50, 70),  # Celsius
                'humidity': (0, 100),      # Percentage
                'pressure': (800, 1200),   # hPa
                'rainfall': (0, 1000),     # mm
                'wind_speed': (0, 200),    # km/h
            }
            
            # Get range based on channel range_group or title
            range_key = channel.range_group.lower() if channel.range_group else None
            if not range_key:
                # Try to infer from title
                title_lower = channel.title.lower()
                for key in ranges.keys():
                    if key in title_lower:
                        range_key = key
                        break
            
            if range_key and range_key in ranges:
                min_val, max_val = ranges[range_key]
                if not (min_val <= numeric_value <= max_val):
                    raise ValidationError(f'Value {numeric_value} outside expected range {min_val}-{max_val}')
            
            return numeric_value
            
        except (ValueError, TypeError):
            raise ValidationError(f'Invalid numeric value: {value}')

    @staticmethod
    def validate_timestamp(timestamp_str):
        """Validate and parse timestamp"""
        try:
            # Handle various timestamp formats
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            
            return datetime.fromisoformat(timestamp_str)
        except ValueError:
            raise ValidationError(f'Invalid timestamp format: {timestamp_str}')

    @staticmethod
    def sanitize_locality_name(name):
        """Sanitize locality names"""
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[^\w\s-]', '', name)
        return sanitized.strip()





### Performance Optimization

from django.core.cache import cache
from django.db import transaction
import hashlib
from django.core.exceptions import ValidationError

class EMSDataProcessor:
    """Optimized processor for EMS data"""
    
    @staticmethod
    def bulk_create_data_points(channel, data_points, interval):
        """Efficiently create multiple data points"""
        objects_to_create = []
        
        for point in data_points:
            try:
                timestamp = EMSDataValidator.validate_timestamp(point['time'])
                value = EMSDataValidator.validate_sensor_value(point['value'], channel)
                
                # Check if data point already exists (avoid duplicates)
                cache_key = f"ems_data_{channel.id}_{timestamp.isoformat()}_{interval}"
                if not cache.get(cache_key):
                    objects_to_create.append(EMSData(
                        channel=channel,
                        timestamp=timestamp,
                        value=value,
                        interval=interval,
                        quality_score=point.get('quality', 1.0),
                        is_validated=True
                    ))
                    # Cache for 1 hour to prevent duplicates
                    cache.set(cache_key, True, 3600)
                    
            except ValidationError as e:
                logger.warning(f"Invalid data point for channel {channel.id}: {e}")
                continue
        
        # Bulk create for efficiency
        if objects_to_create:
            with transaction.atomic():
                EMSData.objects.bulk_create(objects_to_create, ignore_conflicts=True)
        
        return len(objects_to_create)

    @staticmethod
    def cache_latest_values(locality):
        """Cache latest sensor values for fast dashboard loading"""
        cache_key = f"latest_values_{locality.id}"
        
        latest_values = {}
        channels = EMSChannel.objects.filter(locality=locality, is_active=True)
        
        for channel in channels:
            latest_data = EMSData.objects.filter(
                channel=channel
            ).order_by('-timestamp').first()
            
            if latest_data:
                latest_values[channel.id] = {
                    'value': latest_data.value,
                    'timestamp': latest_data.timestamp.isoformat(),
                    'quality': latest_data.quality_score
                }
        
        # Cache for 5 minutes
        cache.set(cache_key, latest_values, 300)
        return latest_values
    
    




## Troubleshooting

### Common Issues and Solutions

#### 1. Callback Endpoints Not Receiving Data

# Test callback accessibility
def test_callback_accessibility():
    """Test if callbacks are accessible from external sources"""
    import subprocess
    import socket
    
    # Check if port is open
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 8000))
    sock.close()
    
    if result == 0:
        print("✓ Port 8000 is open")
    else:
        print("✗ Port 8000 is not accessible")
    
    # Test external accessibility (if deployed)
    try:
        response = requests.get('http://your-domain.com/ems-callback/', timeout=10)
        print(f"✓ Callback endpoint accessible: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Callback endpoint not accessible: {e}")


#### 2. Authentication Token Errors

def debug_auth_token(url):
    """Debug authentication token issues"""
    import urllib.parse
    
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)
    
    if 'auth' in query_params:
        auth_token = query_params['auth'][0]
        print(f"Auth token: {auth_token[:20]}...")
        print(f"Token length: {len(auth_token)}")
        
        # Check token format (should be hex:number)
        if ':' in auth_token:
            token_parts = auth_token.split(':')
            print(f"Token parts: {len(token_parts)}")
            print(f"Hex part length: {len(token_parts[0])}")
        else:
            print("⚠ Token format unexpected")
    else:
        print("✗ No auth token found in URL")


#### 3. Data Processing Errors

def debug_data_processing(callback_payload):
    """Debug data processing issues"""
    try:
        # Validate JSON structure
        required_fields = ['site', 'locName', 'timeZone', 'channels', 'data']
        missing_fields = [field for field in required_fields if field not in callback_payload]
        
        if missing_fields:
            print(f"✗ Missing required fields: {missing_fields}")
            return False
        
        # Test channel URL accessibility
        channels_url = callback_payload['channels']
        try:
            response = requests.get(f"{channels_url}&inclLocality=true", timeout=30)
            print(f"✓ Channels URL accessible: {response.status_code}")
            
            if response.status_code == 200:
                channels_data = response.json()
                print(f"✓ Channels data received: {len(channels_data.get('channels', {}))} channels")
            else:
                print(f"✗ Channels request failed: {response.text}")
                
        except Exception as e:
            print(f"✗ Channels URL error: {e}")
        
        # Test data URLs
        for interval, data_info in callback_payload['data'].items():
            data_url = data_info['url']
            try:
                response = requests.get(data_url, timeout=30)
                print(f"✓ Data URL ({interval}) accessible: {response.status_code}")
            except Exception as e:
                print(f"✗ Data URL ({interval}) error: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Payload processing error: {e}")
        return False


#### 4. Image Download Issues

def debug_image_processing(image_url, save_path):
    """Debug image download and storage"""
    try:
        # Test image URL
        response = requests.get(image_url, timeout=60)
        print(f"Image URL status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"Content-Length: {response.headers.get('Content-Length')}")
        
        if response.status_code == 200:
            # Check if it's actually an image
            if response.headers.get('Content-Type', '').startswith('image/'):
                print("✓ Valid image content")
                
                # Test file saving
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                print(f"✓ Image saved to {save_path}")
                
                # Verify saved file
                import os
                if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                    print("✓ File saved successfully")
                else:
                    print("✗ File save failed")
            else:
                print(f"✗ Not an image: {response.text[:200]}")
        else:
            print(f"✗ Image download failed: {response.text}")
            
    except Exception as e:
        print(f"✗ Image processing error: {e}")

### Monitoring and Alerting

# monitoring.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from .models import EMSLocality, EMSCallbackLog, EMSData
import smtplib
from email.mime.text import MIMEText

class EMSMonitor:
    """Monitor EMS API integration health"""
    
    def __init__(self):
        self.alerts = []
    
    def check_callback_health(self):
        """Check if callbacks are being received regularly"""
        cutoff_time = timezone.now() - timedelta(hours=2)
        
        for locality in EMSLocality.objects.filter(is_active=True):
            if locality.last_callback_received and locality.last_callback_received < cutoff_time:
                self.alerts.append(f"No callbacks received for {locality.loc_name} in 2+ hours")
    
    def check_data_freshness(self):
        """Check if data is being updated regularly"""
        cutoff_time = timezone.now() - timedelta(hours=6)
        
        for locality in EMSLocality.objects.filter(is_active=True):
            recent_data = EMSData.objects.filter(
                channel__locality=locality,
                timestamp__gte=cutoff_time
            ).count()
            
            if recent_data == 0:
                self.alerts.append(f"No recent data for {locality.loc_name} in 6+ hours")
    
    def check_error_rate(self):
        """Check callback error rates"""
        recent_logs = EMSCallbackLog.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=1)
        )
        
        if recent_logs.count() > 0:
            error_rate = recent_logs.filter(success=False).count() / recent_logs.count()
            if error_rate > 0.5:  # More than 50% errors
                self.alerts.append(f"High error rate: {error_rate:.1%} in last hour")
    
    def send_alerts(self):
        """Send alert notifications"""
        if not self.alerts:
            return
        
        message = "EMS API Integration Alerts:\n\n" + "\n".join(self.alerts)
        
        # Send email alert (configure SMTP settings)
        try:
            msg = MIMEText(message)
            msg['Subject'] = 'EMS API Integration Alert'
            msg['From'] = 'alerts@yoursite.com'
            msg['To'] = 'admin@yoursite.com'
            
            # Configure SMTP server
            # server = smtplib.SMTP('your-smtp-server.com', 587)
            # server.starttls()
            # server.login('username', 'password')
            # server.send_message(msg)
            # server.quit()
            
            print("Alert email sent")
        except Exception as e:
            print(f"Failed to send alert email: {e}")
    
    def run_checks(self):
        """Run all monitoring checks"""
        self.check_callback_health()
        self.check_data_freshness()
        self.check_error_rate()
        self.send_alerts()
        
        return len(self.alerts)