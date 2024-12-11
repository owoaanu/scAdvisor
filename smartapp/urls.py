from django.urls import path
from . import views

urlpatterns =  [
    path('', views.index, name='index'),
    path('about', views.about, name='about'),
    path('services', views.services, name='services'),
    path('projects', views.projects, name='projects'),
    path('contact', views.contact, name='contact'),
    path('dashboard', views.leaf_map_view, name='dashboard'),
    path('signup', views.signup, name='signup'),
    path('signin', views.signin, name='signin'),
    path('signout', views.signout, name='signout'),
    # path('drought', views.drought_map_view, name='drought_map_view'),
    # path('map', views.map_view, name='map_view'),
    path('drought', views.leaf_map_view, name='map_view'),
    
]