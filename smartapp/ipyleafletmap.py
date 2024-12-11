from ipyleaflet import (
    Map, GeoJSON, LayersControl, SearchControl, 
    FullScreenControl, DrawControl, 
    basemaps, WidgetControl
)
from ipywidgets import (
    HTML, Layout, Box, VBox, Text,
    Button, Output, Label
)
import json
from IPython.display import display, clear_output

class InteractiveRegionMap:
    def __init__(self, geojson_data, center=[0, 0], zoom=4):
        """
        Initialize interactive map with search and details functionality
        
        Parameters:
        geojson_data: dict or str, GeoJSON data
        center: list, Initial map center coordinates [lat, lon]
        zoom: int, Initial zoom level
        """
        self.geojson_data = (
            json.loads(geojson_data) if isinstance(geojson_data, str) 
            else geojson_data
        )
        
        # Create the base map
        self.map = Map(
            center=center,
            zoom=zoom,
            basemap=basemaps.OpenStreetMap.Mapnik,
            layout=Layout(height='600px')
        )
        
        # Initialize controls and widgets
        self._setup_search()
        self._setup_details_panel()
        self._add_geojson_layer()
        self._add_controls()
    
    def _calculate_bounds(self, feature):
        """Calculate bounds for a GeoJSON feature"""
        coordinates = []
        geometry = feature['geometry']
        
        def extract_coords(coord_list):
            if len(coord_list) == 2 and all(isinstance(c, (int, float)) for c in coord_list):
                coordinates.append(coord_list)
            elif isinstance(coord_list, (list, tuple)):
                for coord in coord_list:
                    extract_coords(coord)
        
        extract_coords(geometry['coordinates'])
        
        if coordinates:
            lats = [coord[1] for coord in coordinates]
            lons = [coord[0] for coord in coordinates]
            return [
                [min(lats), min(lons)],
                [max(lats), max(lons)]
            ]
        return None
    
    def _setup_search(self):
        """Setup search widget and functionality"""
        self.search_widget = Text(
            placeholder='Search regions...',
            layout=Layout(width='250px')
        )
        
        def on_search_change(change):
            search_term = change['new'].lower()
            if search_term:
                for feature in self.geojson_data['features']:
                    if search_term in feature['properties'].get('ADM2_EN', '').lower():
                        # Update details panel
                        self._update_details(feature['properties'])
                        # Zoom to feature
                        bounds = self._calculate_bounds(feature)
                        self.map.fit_bounds(bounds)
                        break
        
        self.search_widget.observe(on_search_change, names='value')
        
        search_control = WidgetControl(
            widget=self.search_widget,
            position='topleft'
        )
        self.map.add_control(search_control)
        
    def _setup_details_panel(self):
        """Setup the details panel widget"""
        self.details_output = Output(
            layout=Layout(
                width='300px',
                max_height='400px',
                overflow='auto',
                border='1px solid #ccc',
                padding='10px',
                background_color='white',
                display='none'
            )
        )
        
        close_button = Button(
            description='×',
            layout=Layout(width='30px')
        )
        
        def close_details(_):
            self.details_output.layout.display = 'none'
            
        close_button.on_click(close_details)
        
        details_container = VBox([
            Box([
                Label('Region Details'),
                close_button
            ], layout=Layout(
                display='flex',
                justify_content='space-between'
            )),
            self.details_output
        ], layout=Layout(
            background_color='white',
            padding='10px',
            border='1px solid #ccc',
            border_radius='4px'
        ))
        
        details_control = WidgetControl(
            widget=details_container,
            position='topright'
        )
        self.map.add_control(details_control)
        
    def _update_details(self, properties):
        """Update the details panel with feature properties"""
        with self.details_output:
            clear_output(wait=True)
            html_content = '<table>'
            for key, value in properties.items():
                html_content += f'<tr><td><strong>{key}:</strong></td><td>{value}</td></tr>'
            html_content += '</table>'
            display(HTML(html_content))
        self.details_output.layout.display = 'block'
        
    def _add_geojson_layer(self):
        """Add GeoJSON layer to the map"""
        style = {
            'opacity': 1,
            'dashArray': '0',
            'fillOpacity': 0.2,
            'weight': 2
        }
        
        hover_style = {
            'fillOpacity': 0.4,
            'weight': 3
        }
        
        self.geojson_layer = GeoJSON(
            data=self.geojson_data,
            style=style,
            hover_style=hover_style
        )
        
        def on_feature_click(feature, **kwargs):
            self._update_details(feature['properties'])
            
        self.geojson_layer.on_click(on_feature_click)
        self.map.add_layer(self.geojson_layer)
        
    def _add_controls(self):
        """Add additional map controls"""
        self.map.add_control(LayersControl())
        self.map.add_control(FullScreenControl())
        
        # Add draw control for additional functionality
        draw_control = DrawControl()
        self.map.add_control(draw_control)
        
    def display(self):
        """Display the map"""
        display(self.map)

# Example usage:
"""
geojson_data = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "name": "Region 1",
                "population": 1000000,
                "area": 5000
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[...coordinates...]]]
            }
        }
    ]
}

map_widget = InteractiveRegionMap(geojson_data)
map_widget.display()
"""