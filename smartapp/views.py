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


# @login_required(redirect_field_name="signin")
# def dashboard(request):
#     return render(request, 'dashboard.html')


@login_required
def dashboard(request):
    localities = EMSLocality.objects.filter(site='NM-AIST').values_list('locName', flat=True).distinct()
    selected_locality = request.GET.get('locality')
    
    images = {}
    if selected_locality:
        images = {
            '1_day': EMSImage.objects.filter(locality__locName=selected_locality, interval='1'),
            '5_days': EMSImage.objects.filter(locality__locName=selected_locality, interval='5'),
            '10_days': EMSImage.objects.filter(locality__locName=selected_locality, interval='10'),
        }
    
    return render(request, 'dashboard.html', {
        'localities': localities,
        'selected_locality': selected_locality,
        'images': images
    })


def leaf_map_view(request):
    return render(request, 'drought_map.html')




import requests
import json
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.http import HttpResponse
from .models import EMSLocality, EMSImage

@csrf_exempt
def ems_callback(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)
    
    site = data.get('site')
    locName = data.get('locName')
    cultures = data.get('cultures', {})
    
    if not site or not locName or not cultures:
        return HttpResponse(status=400)
    
    # Process each culture
    for culture, culData in cultures.items():
        # Get channel metadata
        channels_url = culData['channels']['1']['url'] + "&inclLocality=true"
        try:
            response = requests.get(channels_url)
            response.raise_for_status()
            channels_info = response.json()
        except requests.RequestException:
            continue
        
        # Extract locality info
        locality_info = channels_info['localities'][site][locName]
        locality, _ = EMSLocality.objects.update_or_create(
            site=site,
            locName=locName,
            defaults={
                'title': locality_info.get('title', ''),
                'url': locality_info.get('url', ''),
                'lat': locality_info.get('lat'),
                'lng': locality_info.get('lng'),
                'timezone': locality_info.get('timezone', ''),
            }
        )
        
        # Process images
        for interval in ['1', '5', '10']:  # Selected intervals
            if interval not in culData.get('chart', {}):
                continue
            
            for channel_id, chart_info in culData['chart'][interval].items():
                image_url = chart_info['url'] + "&width=200&height=100"
                try:
                    img_response = requests.get(image_url)
                    img_response.raise_for_status()
                except requests.RequestException:
                    continue
                
                # Save image
                img_name = f"{locName}_{channel_id}_{culture}_{interval}.png"
                img_content = ContentFile(img_response.content)
                
                ems_image = EMSImage(
                    locality=locality,
                    channel_id=int(channel_id),
                    culture=culture,
                    interval=interval
                )
                ems_image.image.save(img_name, img_content)
    
    return HttpResponse(status=200)