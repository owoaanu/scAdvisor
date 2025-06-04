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
        images = {
            '1_day': EMSImage.objects.filter(locality__loc_name=selected_locality, interval='1'),
            '5_days': EMSImage.objects.filter(locality__loc_name=selected_locality, interval='5'),
            '10_days': EMSImage.objects.filter(locality__loc_name=selected_locality, interval='10'),
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
from .models import EMSLocality, EMSChannel, EMSData
from django.core.files.base import ContentFile
from datetime import datetime

@csrf_exempt
def ems_data_callback(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Required fields from callback
        site = data['site']
        loc_name = data['lockame']  # Note: API uses 'lockame' not 'locName'
        timezone = data['timeZone']
        channels_url = data['channels']
        data_intervals = data['data']  # Dict of interval URLs
        
        # Optional field
        last_verified = data.get('lastVerified')
        
        # 1. Get channel information
        channels_response = requests.get(f"{channels_url}&inclLocality=true")
        channels_response.raise_for_status()
        channels_data = channels_response.json()
        
        # 2. Create/update locality
        locality, _ = EMSLocality.objects.update_or_create(
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
            
            # 4. Process data for each interval
            for interval, url_info in data_intervals.items():
                data_url = url_info['url']
                
                # Add format=json if not present
                if 'format=json' not in data_url.lower():
                    data_url += '&format=json' if '?' in data_url else '?format=json'
                
                data_response = requests.get(data_url)
                data_response.raise_for_status()
                interval_data = data_response.json()
                
                # Store data points
                for time_entry in interval_data['time']:
                    for channel_data in interval_data['channels']:
                        EMSData.objects.update_or_create(
                            channel=channel,
                            timestamp=time_entry['timestamp'],
                            interval=interval,
                            defaults={'value': channel_data['value']}
                        )
        
        return JsonResponse({'status': 'success'})
    
    except KeyError as e:
        return JsonResponse({'error': f'Missing required field: {str(e)}'}, status=400)
    except requests.RequestException as e:
        return JsonResponse({'error': f'API request failed: {str(e)}'}, status=502)
    except Exception as e:
        return JsonResponse({'error': f'Processing error: {str(e)}'}, status=500)