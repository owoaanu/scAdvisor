

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








"""
Enhanced views for EMS dashboard with real sensor data integration
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q, Avg, Max, Min
from datetime import datetime, timedelta
import json
import logging

from .models import EMSLocality, EMSChannel, EMSData, EMSImage, EMSSensorData, EMSCallbackLog
from .api_utils import ems_client

logger = logging.getLogger(__name__)

@login_required
def enhanced_dashboard(request):
    """Enhanced dashboard with real sensor data and environmental monitoring"""
    
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
            
            # Get recent trend (last 24 hours)
            yesterday = timezone.now() - timedelta(hours=24)
            recent_data = EMSData.objects.filter(
                channel=channel,
                interval=interval,
                timestamp__gte=yesterday
            ).aggregate(
                avg_value=Avg('value'),
                max_value=Max('value'),
                min_value=Min('value')
            )
            
            channel_info = {
                'channel': channel,
                'latest_data': latest_data,
                'trend': recent_data,
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
    
    # Get recent callback logs for system monitoring
    recent_logs = EMSCallbackLog.objects.order_by('-created_at')[:20]
    
    # Calculate system statistics
    total_localities = device_locations.count()
    active_localities = device_locations.filter(
        last_callback_received__gte=timezone.now() - timedelta(hours=24)
    ).count()
    
    total_sensor_readings = EMSSensorData.objects.count()
    recent_sensor_readings = EMSSensorData.objects.filter(
        timestamp__gte=timezone.now() - timedelta(hours=24)
    ).count()
    
    system_stats = {
        'total_localities': total_localities,
        'active_localities': active_localities,
        'total_sensor_readings': total_sensor_readings,
        'recent_sensor_readings': recent_sensor_readings,
        'system_health': 'good' if active_localities == total_localities else 'warning'
    }
    
    context = {
        'dashboard_data': dashboard_data,
        'selected_locality': selected_locality,
        'selected_interval': interval,
        'available_intervals': [
            ('1', '1 Day'),
            ('5', '5 Days'),
            ('10', '10 Days'),
            ('30', '30 Days'),
            ('60', '60 Days')
        ],
        'recent_logs': recent_logs,
        'system_stats': system_stats
    }
    
    return render(request, 'enhanced_dashboard.html', context)

@login_required
@require_http_methods(["GET"])
def api_sensor_data(request, loc_name):
    """API endpoint to get processed sensor data for a locality"""
    try:
        locality = get_object_or_404(EMSLocality, loc_name=loc_name)
        
        # Get time range
        hours = int(request.GET.get('hours', 24))
        start_time = timezone.now() - timedelta(hours=hours)
        
        # Get sensor data
        sensor_data = EMSSensorData.objects.filter(
            locality=locality,
            timestamp__gte=start_time
        ).order_by('timestamp')
        
        # Format data for charts
        data = {
            'locality': {
                'name': locality.loc_name,
                'title': locality.title,
                'timezone': locality.timezone
            },
            'time_range': {
                'start': start_time.isoformat(),
                'end': timezone.now().isoformat(),
                'hours': hours
            },
            'data_points': []
        }
        
        for reading in sensor_data:
            data_point = {
                'timestamp': reading.timestamp.isoformat(),
                'temperature': reading.temperature,
                'humidity': reading.humidity,
                'pressure': reading.pressure,
                'wind_speed': reading.wind_speed,
                'wind_direction': reading.wind_direction,
                'rainfall': reading.rainfall,
                'solar_radiation': reading.solar_radiation,
                'soil_temperature': reading.soil_temperature,
                'soil_moisture': reading.soil_moisture
            }
            data['data_points'].append(data_point)
        
        return JsonResponse(data)
        
    except Exception as e:
        logger.error(f"Error in api_sensor_data: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["GET"])
def api_locality_summary(request, loc_name):
    """API endpoint to get summary statistics for a locality"""
    try:
        locality = get_object_or_404(EMSLocality, loc_name=loc_name)
        
        # Get latest sensor data
        latest_data = EMSSensorData.objects.filter(
            locality=locality
        ).order_by('-timestamp').first()
        
        # Get 24-hour statistics
        yesterday = timezone.now() - timedelta(hours=24)
        daily_stats = EMSSensorData.objects.filter(
            locality=locality,
            timestamp__gte=yesterday
        ).aggregate(
            avg_temp=Avg('temperature'),
            max_temp=Max('temperature'),
            min_temp=Min('temperature'),
            avg_humidity=Avg('humidity'),
            max_humidity=Max('humidity'),
            min_humidity=Min('humidity'),
            total_rainfall=Avg('rainfall'),  # Sum would be better but Avg for now
            avg_wind_speed=Avg('wind_speed'),
            max_wind_speed=Max('wind_speed')
        )
        
        # Count data points
        data_count = EMSSensorData.objects.filter(
            locality=locality,
            timestamp__gte=yesterday
        ).count()
        
        summary = {
            'locality': {
                'name': locality.loc_name,
                'title': locality.title,
                'last_update': locality.last_callback_received.isoformat() if locality.last_callback_received else None
            },
            'latest_reading': {
                'timestamp': latest_data.timestamp.isoformat() if latest_data else None,
                'temperature': latest_data.temperature if latest_data else None,
                'humidity': latest_data.humidity if latest_data else None,
                'pressure': latest_data.pressure if latest_data else None,
                'wind_speed': latest_data.wind_speed if latest_data else None,
                'rainfall': latest_data.rainfall if latest_data else None
            } if latest_data else None,
            'daily_statistics': {
                'temperature': {
                    'average': round(daily_stats['avg_temp'], 1) if daily_stats['avg_temp'] else None,
                    'maximum': round(daily_stats['max_temp'], 1) if daily_stats['max_temp'] else None,
                    'minimum': round(daily_stats['min_temp'], 1) if daily_stats['min_temp'] else None
                },
                'humidity': {
                    'average': round(daily_stats['avg_humidity'], 1) if daily_stats['avg_humidity'] else None,
                    'maximum': round(daily_stats['max_humidity'], 1) if daily_stats['max_humidity'] else None,
                    'minimum': round(daily_stats['min_humidity'], 1) if daily_stats['min_humidity'] else None
                },
                'wind': {
                    'average_speed': round(daily_stats['avg_wind_speed'], 1) if daily_stats['avg_wind_speed'] else None,
                    'maximum_speed': round(daily_stats['max_wind_speed'], 1) if daily_stats['max_wind_speed'] else None
                },
                'rainfall': round(daily_stats['total_rainfall'], 2) if daily_stats['total_rainfall'] else None,
                'data_points': data_count
            }
        }
        
        return JsonResponse(summary)
        
    except Exception as e:
        logger.error(f"Error in api_locality_summary: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def api_simulate_sensor_data(request):
    """API endpoint to simulate sensor data for testing"""
    try:
        data = json.loads(request.body)
        loc_name = data.get('loc_name')
        
        if not loc_name:
            return JsonResponse({'error': 'loc_name required'}, status=400)
        
        locality = get_object_or_404(EMSLocality, loc_name=loc_name)
        
        # Generate simulated sensor data
        sensor_data = ems_client.fetch_sensor_data(locality)
        
        if sensor_data:
            # Store the simulated data
            ems_client.store_sensor_data(locality, sensor_data)
            
            return JsonResponse({
                'status': 'success',
                'message': f'Simulated sensor data created for {loc_name}',
                'data': sensor_data
            })
        else:
            return JsonResponse({'error': 'Failed to generate sensor data'}, status=500)
            
    except Exception as e:
        logger.error(f"Error in api_simulate_sensor_data: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["GET"])
def api_system_health(request):
    """API endpoint to get system health status"""
    try:
        # Check localities
        total_localities = EMSLocality.objects.filter(is_active=True).count()
        recent_callbacks = EMSLocality.objects.filter(
            is_active=True,
            last_callback_received__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        # Check recent data
        recent_sensor_data = EMSSensorData.objects.filter(
            timestamp__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        # Check callback logs
        recent_errors = EMSCallbackLog.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24),
            success=False
        ).count()
        
        recent_successes = EMSCallbackLog.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24),
            success=True
        ).count()
        
        # Calculate health score
        health_score = 100
        if total_localities > 0:
            callback_ratio = recent_callbacks / total_localities
            if callback_ratio < 0.8:
                health_score -= 30
            elif callback_ratio < 0.9:
                health_score -= 15
        
        if recent_errors > 0 and recent_successes > 0:
            error_ratio = recent_errors / (recent_errors + recent_successes)
            if error_ratio > 0.2:
                health_score -= 25
            elif error_ratio > 0.1:
                health_score -= 10
        
        if recent_sensor_data == 0:
            health_score -= 20
        
        # Determine status
        if health_score >= 90:
            status = 'excellent'
        elif health_score >= 75:
            status = 'good'
        elif health_score >= 50:
            status = 'warning'
        else:
            status = 'critical'
        
        health_data = {
            'status': status,
            'health_score': max(0, health_score),
            'statistics': {
                'total_localities': total_localities,
                'active_localities': recent_callbacks,
                'recent_sensor_readings': recent_sensor_data,
                'recent_callback_errors': recent_errors,
                'recent_callback_successes': recent_successes
            },
            'timestamp': timezone.now().isoformat()
        }
        
        return JsonResponse(health_data)
        
    except Exception as e:
        logger.error(f"Error in api_system_health: {e}")
        return JsonResponse({'error': str(e)}, status=500)

def refresh_dashboard_data(request):
    """Manually refresh dashboard data by simulating sensor readings"""
    try:
        localities = EMSLocality.objects.filter(is_active=True)
        updated_count = 0
        
        for locality in localities:
            # Generate and store simulated sensor data
            sensor_data = ems_client.fetch_sensor_data(locality)
            if sensor_data:
                ems_client.store_sensor_data(locality, sensor_data)
                updated_count += 1
        
        return JsonResponse({
            'status': 'success',
            'message': f'Updated sensor data for {updated_count} localities',
            'updated_localities': updated_count
        })
        
    except Exception as e:
        logger.error(f"Error refreshing dashboard data: {e}")
        return JsonResponse({'error': str(e)}, status=500)

