from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns =  [
    path('', views.index, name='index'),
    path('about', views.about, name='about'),
    path('services', views.services, name='services'),
    path('projects', views.projects, name='projects'),
    path('contact', views.contact, name='contact'),
    # path('dashboard', views.leaf_map_view, name='dashboard'),
    path('signup', views.signup, name='signup'),
    path('signin', views.signin, name='signin'),
    path('signout', views.signout, name='signout'),
    # path('drought', views.drought_map_view, name='drought_map_view'),
    # path('map', views.map_view, name='map_view'),
    path('drought', views.leaf_map_view, name='map_view'),

    # path("ems-callback/", views.ems_callback, name="ems_callback"),

    # path('ems-callback/', views.ems_callback),
    path('ems-data-callback/', views.ems_data_callback, name='ems_callback'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    path('ems-callback/', views.ems_image_callback, name='ems_image_callback'),
     
    ]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)