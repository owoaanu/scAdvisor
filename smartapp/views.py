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

import folium
from  folium import plugins
from branca.element import MacroElement, Template
import geopandas as gpd
import pandas as pd

from .ipyleafletmap import InteractiveRegionMap



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


@login_required(redirect_field_name="signin")
def dashboard(request):
    return render(request, 'dashboard.html')



# def drought_map_view(request):
#     forecasts = [
#     {'region': 'Arusha', 'drought_index': -0.6, 'details': 'Forecast: Moderate drought expected next week.'},
#     {'region': 'Babati', 'drought_index': -1.0, 'details': 'Forecast: Severe drought in the coming 2 weeks.'},
#     {'region': 'Arusha Urban', 'drought_index': -0.9, 'details': 'Forecast: Severe drought, rainfall deficiency likely.'},
#     {'region': 'Babati Urban', 'drought_index': -0.9, 'details': 'Forecast: Severe drought, need for water conservation.'},
#     {'region': 'Bagamoyo', 'drought_index': 0.6, 'details': 'Forecast: Mild conditions, no drought expected.'},
#     ]
    
#     forecasts_df = pd.DataFrame(forecasts)

    
#     # Load Tanzania GeoJSON
#     static_folder = settings.STATICFILES_DIRS[0]
#     tanzania_geojson_url = os.path.join(static_folder,'geojson/tanzaniaBorders.geojson')  # You'll need to provide the actual path
#     tanzania_gdf = gpd.read_file(tanzania_geojson_url)
#     if tanzania_gdf.crs is not None and tanzania_gdf.crs.to_string() != "EPSG:4326":
#         tanzania_gdf = tanzania_gdf.to_crs("EPSG:4326")
        
#     merged_gdf = tanzania_gdf.merge(forecasts_df, left_on='ADM2_EN', right_on='region', how='left')
        
#     # Compute map center
#     tanzania_polygon = tanzania_gdf.union_all()
#     centroid = tanzania_polygon.centroid

#     # -------------------
#     # Create the Folium Map
#     # -------------------
#     min_lon, max_lon = 35.339814,  33.649992 
    
    
#     min_lat, max_lat = -5.595227, -6.040650
    
#     m = folium.Map(
#         location=[centroid.y, centroid.x], 
#         zoom_start=6, 
#         min_zoom=6, 
#         max_bounds=True,
#         min_lat=min_lat,
#         max_lat=max_lat,
#         min_lon=min_lon,
#         max_lon=max_lon,
#         )
    
#     choropleth = folium.Choropleth(
#     geo_data=merged_gdf.__geo_interface__,
#     data=merged_gdf,
#     columns=['region', 'drought_index'],
#     key_on='feature.properties.ADM2_EN',
#     fill_color='RdYlBu',
#     line_color= 'Rd',
#     fill_opacity=0.5,
#     line_opacity=0.6,
#     highlight=True,
#     # legend_name='Drought Severity'
#     ).add_to(m)

    
#     # Add search functionality
#     search = plugins.Search(
#         layer=choropleth.geojson,
#         geom_type='Polygon',
#         placeholder='Search for a region',
#         collapsed=True,
#         search_label='ADM2_EN'
#     ).add_to(m)
    
#     # Add a legend
#     legend_html = '''
#         <div style="position: fixed; bottom: 50px; right: 50px; 
#                     background-color: white; padding: 10px; border-radius: 5px;
#                     z-index: 1000;">
#             <h4>Drought Severity Index</h4>
#             <div><i style="background: #d73027"></i> Severe (>0.8)</div>
#             <div><i style="background: #fc8d59"></i> Moderate (0.6-0.8)</div>
#             <div><i style="background: #fee090"></i> Mild (0.4-0.6)</div>
#             <div><i style="background: #e0f3f8"></i> Normal (<0.4)</div>
#         </div>
#     '''
#     m.get_root().html.add_child(folium.Element(legend_html))
    
    
#     html_template = """
#     {% macro script(this, kwargs) %}
#         // Add an external search box below the map
#         var externalSearch = L.DomUtil.create('div', 'external-search-box');
#         externalSearch.innerHTML = '<input type="text" id="externalSearchBox" placeholder="External Search..." style="width:200px;padding:4px 8px;margin:5px 0;">';
#         // Insert the external search box into the map's container or anywhere else on the page
#         // For simplicity, we'll place it just after the map element
#         var mapContainer = document.getElementById('{{this.get_name()}}');
#         mapContainer.parentNode.insertBefore(externalSearch, mapContainer.nextSibling);

#         // Function to find the search control variable name
#         // The search variable usually looks like 'search_xxxxxx'
#         var searchControl = null;
#         for (var key in window) {
#         if (key.startsWith("search_") && window[key]._input) {
#             // Found the Search control instance
#             searchControl = window[key];
#             break;
#         }
#         }

#         if (searchControl) {
#         // Listen for input changes on the external search box
#         document.getElementById('externalSearchBox').addEventListener('keyup', function(e) {
#             var query = e.target.value.trim();
#             if (query.length > 0) {
#                 // Trigger the search programmatically
#                 searchControl.searchText(query);
#             } else {
#                 // If empty, reset the search (this may vary depending on Leaflet.Control.Search version)
#                 searchControl.collapse();
#             }
#         });
#         }

#         // Optionally hide the original search box:
#         var leafletSearchBox = document.querySelector('.leaflet-control-search');
#         if (leafletSearchBox) {
#             leafletSearchBox.style.display = 'none';
#         }
#     {% endmacro %}
#     """

#     # Add our custom template with the external input to the map
#     class ExternalSearch(MacroElement):
#         _template = Template(html_template)
#         def __init__(self):
#             super().__init__()

#     m.add_child(ExternalSearch())
#     # m.get_root().html.add_child(folium.Element("""
#     #     <div style="">
#     #         <h5>Hello World!!!</h5>
#     #         <button>Test Button</button>
#     #     </div>
#     #     """))
    
#     # Save the map to HTML
#     map_html = m._repr_html_()
    
#     return render(request, 'drought_map.html', {'map': map_html})

# def map_view(request):
    
#     # static_folder = settings.STATICFILES_DIRS[0]
#     # tanzania_geojson_url = os.path.join(static_folder,'geojson/tanzaniaBorders.geojson')  # You'll need to provide the actual path
    
#     # with open(tanzania_geojson_url) as f:
#     #     geojson_data = json.load(f)
    
#     geojson_data = {
#         "type": "FeatureCollection",
#         "features": [
#             {
#                 "type": "Feature",
#                 "properties": {
#                     "name": "Arusha",
#                     "description": "A city in northern Tanzania, known for its tourism.",
#                     "population": 416442
#                 },
#                 "geometry": {
#                     "type": "Point",
#                     "coordinates": [36.68, -3.37]
#                 }
#             },
#             # ... more features ...
#         ]
#     }        
        
#     map_widget = InteractiveRegionMap(geojson_data)
#     return render(request, 'drought_map.html', {'map': map_widget.map})

def leaf_map_view(request):
        
    return render(request, 'drought_map.html')