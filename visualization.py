"""
Visualization module for shade routing results.
Creates interactive maps showing routes with shade information.
"""

import folium
import geopandas as gpd
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from shapely.geometry import Point, LineString, Polygon
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns

logger = logging.getLogger(__name__)

class RouteVisualizer:
    """Visualizes shade routing results on interactive maps."""
    
    def __init__(self):
        """Initialize the route visualizer."""
        self.base_map = None
        self.color_palette = 'RdYlBu_r'  # Red (no shade) to Blue (full shade)
    
    def create_base_map(self, 
                       center_point: Tuple[float, float] = (40.7128, -74.0060),
                       zoom_start: int = 13) -> folium.Map:
        """
        Create a base Folium map centered on NYC.
        
        Args:
            center_point: (lat, lon) center point for the map
            zoom_start: Initial zoom level
            
        Returns:
            Folium map object
        """
        try:
            logger.info(f"Creating base map centered on {center_point}")
            
            # Create base map with OpenStreetMap tiles
            base_map = folium.Map(
                location=center_point,
                zoom_start=zoom_start,
                tiles='OpenStreetMap',
                control_scale=True
            )
            
            # Add additional tile layers
            folium.TileLayer(
                tiles='CartoDB positron',
                name='Light Map',
                overlay=False,
                control=True
            ).add_to(base_map)
            
            folium.TileLayer(
                tiles='CartoDB dark_matter',
                name='Dark Map',
                overlay=False,
                control=True
            ).add_to(base_map)
            
            self.base_map = base_map
            return base_map
            
        except Exception as e:
            logger.error(f"Error creating base map: {e}")
            raise
    
    def add_route_to_map(self, 
                         route_info: Dict,
                         map_obj: Optional[folium.Map] = None,
                         route_name: str = "Route",
                         show_shade_scores: bool = True) -> folium.Map:
        """
        Add a route to the map with shade information.
        
        Args:
            route_info: Route information from ShadeRouter
            map_obj: Folium map object (creates new one if None)
            route_name: Name for the route legend
            show_shade_scores: Whether to show shade scores on segments
            
        Returns:
            Updated Folium map
        """
        try:
            if map_obj is None:
                map_obj = self.base_map or self.create_base_map()
            
            logger.info(f"Adding route '{route_name}' to map")
            
            # Create color map for shade scores
            shade_scores = [edge['shade_score'] for edge in route_info['edges']]
            colors = self._get_shade_colors(shade_scores)
            
            # Add route segments
            for i, edge in enumerate(route_info['edges']):
                # Create popup with segment information
                popup_text = f"""
                <b>{route_name} - Segment {i+1}</b><br>
                Distance: {edge['distance_m']:.0f}m<br>
                Shade Score: {edge['shade_score']:.2f}<br>
                Start: ({edge['start'][1]:.4f}, {edge['start'][0]:.4f})<br>
                End: ({edge['end'][1]:.4f}, {edge['end'][0]:.4f})
                """
                
                # Convert geometry to lat/lon for Folium
                coords = list(edge['geometry'].coords)
                lat_lon_coords = [(coord[1], coord[0]) for coord in coords]  # (lat, lon)
                
                # Add route segment
                folium.PolyLine(
                    locations=lat_lon_coords,
                    color=colors[i],
                    weight=6,
                    opacity=0.8,
                    popup=folium.Popup(popup_text, max_width=300),
                    tooltip=f"Shade: {edge['shade_score']:.2f}"
                ).add_to(map_obj)
                
                # Add shade score labels if requested
                if show_shade_scores:
                    # Place label at midpoint of segment
                    mid_idx = len(lat_lon_coords) // 2
                    mid_point = lat_lon_coords[mid_idx]
                    
                    folium.Marker(
                        location=mid_point,
                        icon=folium.DivIcon(
                            html=f'<div style="background-color: white; border: 1px solid black; padding: 2px; font-size: 10px;">{edge["shade_score"]:.2f}</div>',
                            icon_size=(50, 20),
                            icon_anchor=(25, 10)
                        ),
                        popup=f"Shade Score: {edge['shade_score']:.2f}"
                    ).add_to(map_obj)
            
            # Add start and end markers
            start_lat, start_lon = route_info['start_point']
            end_lat, end_lon = route_info['end_point']
            
            folium.Marker(
                location=(start_lat, start_lon),
                popup=f"<b>Start</b><br>{route_name}<br>Lat: {start_lat:.4f}<br>Lon: {start_lon:.4f}",
                icon=folium.Icon(color='green', icon='play')
            ).add_to(map_obj)
            
            folium.Marker(
                location=(end_lat, end_lon),
                popup=f"<b>End</b><br>{route_name}<br>Lat: {end_lat:.4f}<br>Lon: {end_lon:.4f}",
                icon=folium.Icon(color='red', icon='stop')
            ).add_to(map_obj)
            
            # Add route summary
            summary_text = f"""
            <b>{route_name} Summary</b><br>
            Total Distance: {route_info['total_distance_km']:.2f} km<br>
            Average Shade: {route_info['average_shade_score']:.2f}<br>
            Segments: {route_info['num_segments']}<br>
            Date: {route_info['date']}<br>
            Time: {route_info['time_of_day']}
            """
            
            folium.Marker(
                location=(start_lat + 0.001, start_lon + 0.001),  # Offset slightly
                icon=folium.DivIcon(
                    html=f'<div style="background-color: white; border: 2px solid black; padding: 5px; font-size: 12px; max-width: 200px;">{summary_text}</div>',
                    icon_size=(200, 100),
                    icon_anchor=(100, 50)
                )
            ).add_to(map_obj)
            
            return map_obj
            
        except Exception as e:
            logger.error(f"Error adding route to map: {e}")
            raise
    
    def add_multiple_routes(self, 
                           routes: List[Dict],
                           map_obj: Optional[folium.Map] = None) -> folium.Map:
        """
        Add multiple routes to the same map with different colors.
        
        Args:
            routes: List of route information dictionaries
            map_obj: Folium map object (creates new one if None)
            
        Returns:
            Updated Folium map
        """
        try:
            if map_obj is None:
                # Center map on first route
                center_lat = (routes[0]['start_point'][0] + routes[0]['end_point'][0]) / 2
                center_lon = (routes[0]['start_point'][1] + routes[0]['end_point'][1]) / 2
                map_obj = self.create_base_map((center_lat, center_lon))
            
            # Define colors for different routes
            route_colors = ['blue', 'red', 'green', 'purple', 'orange', 'brown']
            
            for i, route in enumerate(routes):
                route_name = f"Route {i+1}"
                if 'weight_combination' in route:
                    route_name += f" ({route['weight_combination']})"
                
                # Use different color for each route
                self.color_palette = route_colors[i % len(route_colors)]
                
                map_obj = self.add_route_to_map(
                    route, map_obj, route_name, show_shade_scores=False
                )
            
            # Add legend
            legend_html = """
            <div style="position: fixed; 
                        bottom: 50px; left: 50px; width: 200px; height: 120px; 
                        background-color: white; border:2px solid grey; z-index:9999; 
                        font-size:14px; padding: 10px">
            <p><b>Route Legend</b></p>
            """
            
            for i, route in enumerate(routes):
                color = route_colors[i % len(route_colors)]
                route_name = f"Route {i+1}"
                if 'weight_combination' in route:
                    route_name += f" ({route['weight_combination']})"
                
                legend_html += f'<p><span style="color:{color};">●</span> {route_name}</p>'
            
            legend_html += "</div>"
            map_obj.get_root().html.add_child(folium.Element(legend_html))
            
            return map_obj
            
        except Exception as e:
            logger.error(f"Error adding multiple routes: {e}")
            raise
    
    def add_shade_heatmap(self, 
                          street_network: gpd.GeoDataFrame,
                          shade_scores: List[float],
                          map_obj: Optional[folium.Map] = None) -> folium.Map:
        """
        Add a heatmap layer showing shade scores across the street network.
        
        Args:
            street_network: GeoDataFrame with street segments
            shade_scores: List of shade scores corresponding to street segments
            map_obj: Folium map object (creates new one if None)
            
        Returns:
            Updated Folium map
        """
        try:
            if map_obj is None:
                map_obj = self.base_map or self.create_base_map()
            
            logger.info("Adding shade heatmap to map")
            
            # Prepare heatmap data
            heatmap_data = []
            
            for idx, row in street_network.iterrows():
                if idx < len(shade_scores):
                    shade_score = shade_scores[idx]
                    
                    # Sample points along the street segment for heatmap
                    geometry = row['geometry']
                    if geometry.is_valid and not geometry.is_empty:
                        coords = list(geometry.coords)
                        if len(coords) >= 2:
                            # Sample every 10 meters along the segment
                            segment_length = geometry.length
                            num_samples = max(2, int(segment_length / 10))
                            
                            for i in range(num_samples):
                                t = i / (num_samples - 1) if num_samples > 1 else 0
                                point = geometry.interpolate(t, normalized=True)
                                
                                # Convert to lat/lon for heatmap
                                lat, lon = point.y, point.x
                                heatmap_data.append([lat, lon, shade_score])
            
            # Add heatmap layer
            folium.plugins.HeatMap(
                data=heatmap_data,
                radius=15,
                blur=10,
                max_zoom=13,
                gradient={0.0: 'red', 0.5: 'yellow', 1.0: 'blue'},
                name='Shade Heatmap'
            ).add_to(map_obj)
            
            return map_obj
            
        except Exception as e:
            logger.error(f"Error adding shade heatmap: {e}")
            raise
    
    def create_shade_analysis_plot(self, route_info: Dict) -> plt.Figure:
        """
        Create a matplotlib plot analyzing shade distribution along the route.
        
        Args:
            route_info: Route information dictionary
            
        Returns:
            Matplotlib figure
        """
        try:
            logger.info("Creating shade analysis plot")
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # Extract data
            distances = []
            shade_scores = []
            cumulative_distance = 0
            
            for edge in route_info['edges']:
                distances.append(cumulative_distance)
                shade_scores.append(edge['shade_score'])
                cumulative_distance += edge['distance_m']
            
            # Plot 1: Shade score vs distance
            ax1.plot(distances, shade_scores, 'b-o', linewidth=2, markersize=6)
            ax1.set_xlabel('Distance (m)')
            ax1.set_ylabel('Shade Score')
            ax1.set_title(f'Shade Distribution Along Route\nTotal Distance: {route_info["total_distance_km"]:.2f} km, Avg Shade: {route_info["average_shade_score"]:.2f}')
            ax1.grid(True, alpha=0.3)
            ax1.set_ylim(0, 1)
            
            # Add horizontal line for average
            avg_shade = np.mean(shade_scores)
            ax1.axhline(y=avg_shade, color='r', linestyle='--', alpha=0.7, label=f'Average: {avg_shade:.2f}')
            ax1.legend()
            
            # Plot 2: Histogram of shade scores
            ax2.hist(shade_scores, bins=10, alpha=0.7, color='skyblue', edgecolor='black')
            ax2.set_xlabel('Shade Score')
            ax2.set_ylabel('Frequency')
            ax2.set_title('Distribution of Shade Scores')
            ax2.grid(True, alpha=0.3)
            ax2.axvline(x=avg_shade, color='r', linestyle='--', alpha=0.7, label=f'Average: {avg_shade:.2f}')
            ax2.legend()
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            logger.error(f"Error creating shade analysis plot: {e}")
            raise
    
    def _get_shade_colors(self, shade_scores: List[float]) -> List[str]:
        """Get colors for shade scores using a color palette."""
        try:
            # Normalize shade scores to 0-1 range
            normalized_scores = np.array(shade_scores)
            
            # Create color map
            cmap = plt.cm.get_cmap(self.color_palette)
            
            # Convert to hex colors
            colors = [mcolors.to_hex(cmap(score)) for score in normalized_scores]
            
            return colors
            
        except Exception as e:
            logger.error(f"Error getting shade colors: {e}")
            # Fallback to blue for all segments
            return ['#0000FF'] * len(shade_scores)
    
    def save_map(self, 
                 map_obj: folium.Map,
                 filename: str = "shade_route_map.html") -> str:
        """
        Save the map to an HTML file.
        
        Args:
            map_obj: Folium map object
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        try:
            logger.info(f"Saving map to {filename}")
            map_obj.save(filename)
            return filename
            
        except Exception as e:
            logger.error(f"Error saving map: {e}")
            raise
    
    def create_route_summary_table(self, routes: List[Dict]) -> str:
        """
        Create an HTML table summarizing multiple routes.
        
        Args:
            routes: List of route information dictionaries
            
        Returns:
            HTML table string
        """
        try:
            html = """
            <table border="1" style="border-collapse: collapse; width: 100%; margin: 20px 0;">
                <tr style="background-color: #f2f2f2;">
                    <th style="padding: 8px; text-align: left;">Route</th>
                    <th style="padding: 8px; text-align: left;">Distance (km)</th>
                    <th style="padding: 8px; text-align: left;">Avg Shade</th>
                    <th style="padding: 8px; text-align: left;">Segments</th>
                    <th style="padding: 8px; text-align: left;">Weights</th>
                </tr>
            """
            
            for i, route in enumerate(routes):
                route_name = f"Route {i+1}"
                weights = route.get('weight_combination', 'Default')
                
                html += f"""
                <tr>
                    <td style="padding: 8px;">{route_name}</td>
                    <td style="padding: 8px;">{route['total_distance_km']:.2f}</td>
                    <td style="padding: 8px;">{route['average_shade_score']:.3f}</td>
                    <td style="padding: 8px;">{route['num_segments']}</td>
                    <td style="padding: 8px;">{weights}</td>
                </tr>
                """
            
            html += "</table>"
            return html
            
        except Exception as e:
            logger.error(f"Error creating route summary table: {e}")
            return f"<p>Error creating summary table: {e}</p>"
