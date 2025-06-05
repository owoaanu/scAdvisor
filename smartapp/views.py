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


@login_required
def dashboard(request):
    localities = EMSLocality.objects.filter(site='NM-AIST').values_list('loc_name', flat=True).distinct()
    selected_locality = request.GET.get('locality')
    
    channels = []
    images = {}
    
    if selected_locality:
        try:
            locality = EMSLocality.objects.get(loc_name=selected_locality)
            channels = EMSChannel.objects.filter(locality=locality)
            
            # Get images grouped by interval
            images = {
                '1_day': EMSImage.objects.filter(locality=locality, interval='1').select_related('channel'),
                '5_days': EMSImage.objects.filter(locality=locality, interval='5').select_related('channel'),
                '10_days': EMSImage.objects.filter(locality=locality, interval='10').select_related('channel'),
            }
        except EMSLocality.DoesNotExist:
            messages.warning(request, 'Selected locality not found')
    
    return render(request, 'dashboard.html', {
        'localities': localities,
        'selected_locality': selected_locality,
        'channels': channels,
        'images': images
    })


def leaf_map_view(request):
    return render(request, 'drought_map.html')




import requests
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import EMSLocality, EMSChannel, EMSData, EMSImage  # Add EMSImage
from django.core.files.base import ContentFile
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def ems_data_callback(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)
    
    try:
        # Ensure we have a request body
        if not request.body:
            return JsonResponse({'error': 'Empty request body'}, status=400)
            
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError as e:
            return JsonResponse({'error': f'Invalid JSON: {str(e)}'}, status=400)
        
        # Required fields validation
        required_fields = ['site', 'locName', 'timeZone', 'channels', 'data']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'error': f'Missing required field: {field}'}, status=400)
        
        # Process the data
        site = data['site']
        loc_name = data['locName']
        timezone = data['timeZone']
        channels_url = data['channels']
        data_intervals = data['data']
        last_verified = data.get('lastVerified')
        
        # Get channel information
        try:
            channels_response = requests.get(f"{channels_url}&inclLocality=true")
            channels_response.raise_for_status()
            channels_data = channels_response.json()
        except Exception as e:
            return JsonResponse({'error': f'Failed to fetch channels: {str(e)}'}, status=400)
        
        # Create/update locality
        locality, _ = EMSLocality.objects.update_or_create(
            site=site,
            loc_name=loc_name,
            defaults={
                'timezone': timezone,
                'last_verified': datetime.fromisoformat(last_verified) if last_verified else None
            }
        )
        
        # Process channels
        for channel_id, channel_info in channels_data.get('channels', {}).items():
            EMSChannel.objects.update_or_create(
                locality=locality,
                channel_id=int(channel_id),
                defaults={
                    'title': channel_info.get('title', ''),
                    'default_title': channel_info.get('defaultTitle', channel_info.get('title', '')),
                    'range_group': channel_info.get('rangeGroup', '')
                }
            )
        
        return JsonResponse({'status': 'success'})
    
    except Exception as e:
        return JsonResponse({'error': f'Processing error: {str(e)}'}, status=500)


@csrf_exempt
def ems_image_callback(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)
    
    try:
        # Ensure we have a request body
        if not request.body:
            return JsonResponse({'error': 'Empty request body'}, status=400)
            
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError as e:
            return JsonResponse({'error': f'Invalid JSON: {str(e)}'}, status=400)
        
        # Required fields validation
        required_fields = ['site', 'locName', 'cultures']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'error': f'Missing required field: {field}'}, status=400)
        
        site = data['site']
        loc_name = data['locName']
        cultures = data['cultures']
        
        try:
            locality = EMSLocality.objects.get(site=site, loc_name=loc_name)
        except EMSLocality.DoesNotExist:
            return JsonResponse({'error': 'Locality not found'}, status=404)
        
        for culture, culData in cultures.items():
            # Get channel metadata
            try:
                channels_url = culData['channels']['1']['url']
                channels_response = requests.get(f"{channels_url}&inclLocality=true")
                channels_data = channels_response.json()
            except Exception as e:
                continue  # Skip this culture if we can't get channels
            
            # Process each interval
            for interval in ['1', '5', '10']:
                if interval not in culData.get('chart', {}):
                    continue
                
                for channel_id, chart_info in culData['chart'][interval].items():
                    try:
                        # Download chart image
                        chart_url = f"{chart_info['url']}&width=600&height=400"
                        img_response = requests.get(chart_url)
                        img_response.raise_for_status()
                        
                        # Get channel - THIS IS WHERE THE FIX IS
                        channel = EMSChannel.objects.get(
                            locality=locality,
                            channel_id=int(channel_id))
                        
                        # Save image
                        img_name = f"chart_{loc_name}_{channel_id}_{interval}_{culture}.png"
                        ems_image, created = EMSImage.objects.update_or_create(
                            locality=locality,
                            channel=channel,
                            interval=interval,
                            culture=culture,
                            defaults={'image': ContentFile(img_response.content, name=img_name)}
                        )
                    except EMSChannel.DoesNotExist:
                        continue  # Skip if channel doesn't exist
                    except Exception as e:
                        continue  # Skip this image if there's an error
        
        return JsonResponse({'status': 'success'})
    
    except Exception as e:
        return JsonResponse({'error': f'Processing error: {str(e)}'}, status=500)