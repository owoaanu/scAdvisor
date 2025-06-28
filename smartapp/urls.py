from django.urls import path
from . import views
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
    
    # EMS API Callbacks
    path('ems-callback/', views.ems_data_callback, name='ems_callback'),
    path('ems-image-callback/', views.ems_image_callback, name='ems_image_callback'),
    
    # API Endpoints for Dashboard
    path('api/locality/<str:loc_name>/data/', views.api_locality_data, name='api_locality_data'),
    path('api/locality/<str:loc_name>/images/', views.api_locality_images, name='api_locality_images'),
    
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
