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
    
    images = {}
    if selected_locality:
        # Get images for selected locality
        locality = EMSLocality.objects.get(loc_name=selected_locality)
        images = {
            '1_day': EMSImage.objects.filter(locality=locality, interval='1'),
            '5_days': EMSImage.objects.filter(locality=locality, interval='5'),
            '10_days': EMSImage.objects.filter(locality=locality, interval='10'),
        }
    
    return render(request, 'dashboard.html', {
        'localities': localities,
        'selected_locality': selected_locality,
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
        # Log raw request body for debugging
        raw_body = request.body.decode('utf-8')
        logger.info(f"Received callback: {raw_body}")
        data = json.loads(raw_body)
        
        # Required fields from callback
        site = data['site']
        loc_name = data['lockame']
        timezone = data['timeZone']
        channels_url = data['channels']
        data_intervals = data['data']  # Dict of interval URLs
        
        # Optional field
        last_verified = data.get('lastVerified')
        
        # 1. Get channel information
        channels_response = requests.get(f"{channels_url}&inclLocality=true")
        channels_response.raise_for_status()
        
        try:
            channels_data = channels_response.json()
        except json.JSONDecodeError:
            logger.error(f"Failed to parse channels JSON. Response: {channels_response.text}")
            return JsonResponse({'error': 'Invalid channels JSON'}, status=400)
        
        # 2. Create/update locality
        locality, created = EMSLocality.objects.update_or_create(
            site=site,
            loc_name=loc_name,
            defaults={
                'timezone': timezone,
                'last_verified': datetime.fromisoformat(last_verified) if last_verified else None
            }
        )
        
        # 3. Process channels
        for channel_id, channel_info in channels_data['channels'].items():
            channel, _ = EMSChannel.objects.update_or_create(
                locality=locality,
                channel_id=int(channel_id),
                defaults={
                    'title': channel_info['title'],
                    'default_title': channel_info.get('defaultTitle', channel_info['title']),
                    'range_group': channel_info['rangeGroup']
                }
            )
        
        return JsonResponse({'status': 'success'})
    
    except KeyError as e:
        logger.error(f"Missing key in request: {str(e)}")
        return JsonResponse({'error': f'Missing required field: {str(e)}'}, status=400)
    except requests.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        return JsonResponse({'error': f'API request failed: {str(e)}'}, status=502)
    except Exception as e:
        logger.exception("Processing error")
        return JsonResponse({'error': f'Processing error: {str(e)}'}, status=500)
    
    
    
@csrf_exempt
def ems_image_callback(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        site = data['site']
        loc_name = data['locName']
        cultures = data['cultures']
        
        locality = EMSLocality.objects.get(site=site, loc_name=loc_name)
        
        for culture, culData in cultures.items():
            # Get channel metadata using the shortest interval
            channels_url = culData['channels']['1']['url']
            channels_response = requests.get(f"{channels_url}&inclLocality=true")
            channels_data = channels_response.json()
            
            # Process each interval
            for interval in ['1', '5', '10']:  # Only process needed intervals
                for channel_id, chart_info in culData['chart'][interval].items():
                    # Download chart image
                    chart_url = chart_info['url'] + "&width=600&height=400"
                    img_response = requests.get(chart_url)
                    img_response.raise_for_status()
                    
                    # Get channel object
                    channel = EMSChannel.objects.get(
                        locality=locality,
                        channel_id=int(channel_id)
                    )
                    
                    # Save image to model
                    img_name = f"chart_{loc_name}_{channel_id}_{interval}_{culture}.png"
                    ems_image = EMSImage(
                        locality=locality,
                        channel=channel,
                        interval=interval,
                        culture=culture
                    )
                    ems_image.image.save(img_name, ContentFile(img_response.content))
        
        return JsonResponse({'status': 'success'})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)