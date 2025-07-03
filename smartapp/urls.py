from django.urls import path
from . import views
from .enhanced_views import (
    enhanced_dashboard, api_sensor_data, api_locality_summary, 
    api_simulate_sensor_data, api_system_health, refresh_dashboard_data
)
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('', views.index, name='index'),
    path('about', views.about, name='about'),
    path('services', views.services, name='services'),
    path('projects', views.projects, name='projects'),
    path('contact', views.contact, name='contact'),
    
    path('signup', views.signup, name='signup'),
    path('signin', views.signin, name='signin'),
    path('signout', views.signout, name='signout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('enhanced-dashboard/', enhanced_dashboard, name='enhanced_dashboard'),
    
    # EMS API Callbacks
    path('ems-callback/', views.ems_data_callback, name='ems_callback'),
    path('ems-image-callback/', views.ems_image_callback, name='ems_image_callback'),
    
    # API Endpoints for Dashboard
    path('api/locality/<str:loc_name>/data/', views.api_locality_data, name='api_locality_data'),
    path('api/locality/<str:loc_name>/images/', views.api_locality_images, name='api_locality_images'),
    
    # Enhanced API Endpoints
    path('api/locality/<str:loc_name>/sensor-data/', api_sensor_data, name='api_sensor_data'),
    path('api/locality/<str:loc_name>/summary/', api_locality_summary, name='api_locality_summary'),
    path('api/simulate-sensor-data/', api_simulate_sensor_data, name='api_simulate_sensor_data'),
    path('api/system-health/', api_system_health, name='api_system_health'),
    path('api/refresh-dashboard/', refresh_dashboard_data, name='refresh_dashboard_data'),
    
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
