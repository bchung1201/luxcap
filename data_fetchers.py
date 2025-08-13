"""
Data fetching module for NYC Shade Router project.
Fetches street network via OSMnx and building data from NYC Open Data.
"""

import os
import requests
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point, Polygon
from typing import Dict, List, Any, Optional
import config

class NYCDataFetcher:
    """Fetches NYC data from various sources."""
    
    def __init__(self):
        self.app_token = os.getenv("NYC_APP_TOKEN")
        self.base_url = "https://data.cityofnewyork.us/resource"
        
    def nyc_get(self, dataset: str, params: Optional[Dict] = None, geojson: bool = True) -> Dict:
        """Fetch data from NYC Open Data API.
        
        Args:
            dataset: Dataset ID (e.g., '5zhs-2jue' for buildings)
            params: Query parameters (e.g., {'$limit': 1000})
            geojson: Whether to request GeoJSON format
            
        Returns:
            API response as JSON
        """
        ext = "geojson" if geojson else "json"
        url = f"{self.base_url}/{dataset}.{ext}"
        
        headers = {"X-App-Token": self.app_token} if self.app_token else {}
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def fetch_buildings_near_location(self, lat: float, lon: float, radius_meters: int = 500, limit: int = 5000) -> List[Dict]:
        """Fetch buildings near a specific location with heights using ArcGIS API.
        
        Args:
            lat: Latitude of center point
            lon: Longitude of center point  
            radius_meters: Search radius in meters
            limit: Maximum number of results
            
        Returns:
            List of building data with heights
        """
        try:
            # Use ArcGIS REST API instead of NYC Open Data
            base_url = "https://services6.arcgis.com/yG5s3afENB5iO9fj/arcgis/rest/services/BUILDING_view/FeatureServer/0"
            
            # For now, let's just get a sample of buildings and filter locally
            # This ensures we get some data for shade calculations
            query_url = f"{base_url}/query"
            params = {
                'where': '1=1',  # Get all buildings
                'outFields': 'OBJECTID,BIN,HEIGHT_ROOF,GROUND_ELEVATION,NAME,Shape__Area,Shape__Length',
                'f': 'json',
                'resultRecordCount': min(limit, 1000),  # ArcGIS has limits
                'returnGeometry': 'true',
                'outSR': '4326'  # WGS84 coordinate system
            }
            
            response = requests.get(query_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'features' in data and data['features']:
                print(f"  ArcGIS returned {len(data['features'])} total buildings")
                buildings = []
                processed_count = 0
                within_radius_count = 0
                
                for feature in data['features']:
                    attrs = feature.get('attributes', {})
                    geom = feature.get('geometry', {})
                    
                    # Extract coordinates from geometry if available
                    building_lat, building_lon = None, None
                    if geom and 'rings' in geom:  # Polygon geometry
                        # Get centroid of the building polygon
                        try:
                            rings = geom['rings']
                            if rings and len(rings) > 0:
                                # Calculate centroid of first ring
                                coords = rings[0]
                                if len(coords) > 0:
                                    # Simple centroid calculation
                                    x_sum = sum(coord[0] for coord in coords)
                                    y_sum = sum(coord[1] for coord in coords)
                                    building_lon = x_sum / len(coords)
                                    building_lat = y_sum / len(coords)
                                    processed_count += 1
                        except Exception as e:
                            pass
                    
                    # Only include buildings with valid coordinates and within radius
                    if building_lat is not None and building_lon is not None:
                        # Calculate distance
                        distance = ((building_lat - lat) ** 2 + (building_lon - lon) ** 2) ** 0.5
                        if distance * 111320 <= radius_meters:  # Convert degrees to meters
                            within_radius_count += 1
                            building = {
                                'bin': attrs.get('BIN'),
                                'height_roof': attrs.get('HEIGHT_ROOF'),
                                'ground_elevation': attrs.get('GROUND_ELEVATION'),
                                'name': attrs.get('NAME'),
                                'latitude': building_lat,
                                'longitude': building_lon,
                                'geometry': geom
                            }
                            buildings.append(building)
                
                print(f"  Processed {processed_count} buildings with valid geometry")
                print(f"  Found {within_radius_count} buildings within {radius_meters}m radius")
                
                # If we don't have enough buildings in the radius, expand the search
                if len(buildings) < 10 and radius_meters < 10000:  # Less than 10 buildings and radius < 10km
                    print(f"  Expanding search radius to get more buildings for shade calculations...")
                    # Return all processed buildings for now, we'll filter by distance later in the shade calculation
                    all_buildings = []
                    for feature in data['features']:
                        attrs = feature.get('attributes', {})
                        geom = feature.get('geometry', {})
                        
                        if geom and 'rings' in geom:
                            try:
                                rings = geom['rings']
                                if rings and len(rings) > 0:
                                    coords = rings[0]
                                    if len(coords) > 0:
                                        x_sum = sum(coord[0] for coord in coords)
                                        y_sum = sum(coord[1] for coord in coords)
                                        building_lon = x_sum / len(coords)
                                        building_lat = y_sum / len(coords)
                                        
                                        building = {
                                            'bin': attrs.get('BIN'),
                                            'height_roof': attrs.get('HEIGHT_ROOF'),
                                            'ground_elevation': attrs.get('GROUND_ELEVATION'),
                                            'name': attrs.get('NAME'),
                                            'latitude': building_lat,
                                            'longitude': building_lon,
                                            'geometry': geom
                                        }
                                        all_buildings.append(building)
                            except:
                                continue
                    
                    print(f"  Returning {len(all_buildings)} buildings for expanded shade calculations")
                    return all_buildings
                
                print(f"Fetched {len(buildings)} buildings near ({lat}, {lon}) from ArcGIS API")
                return buildings
            else:
                print("No buildings found in response")
                return []
                
        except Exception as e:
            print(f"Error fetching buildings from ArcGIS: {e}")
            return []
    
    def fetch_street_network(self, center_lat: float, center_lon: float, radius_km: float = 2.0) -> Any:
        """Fetch street network using OSMnx.
        
        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            radius_km: Search radius in kilometers
            
        Returns:
            OSMnx graph object
        """
        try:
            # Use the newer OSMnx API
            G = ox.graph_from_point((center_lat, center_lon), dist=radius_km*1000, network_type='walk')
            print(f"Fetched street network with {len(G.nodes)} nodes and {len(G.edges)} edges")
            return G
            
        except Exception as e:
            print(f"Error fetching street network: {e}")
            return None
    
    def get_street_segments_from_network(self, G) -> List[Dict]:
        """Extract street segments from OSMnx network graph.
        
        Args:
            G: OSMnx graph object
            
        Returns:
            List of street segment data with geometry and properties
        """
        try:
            # Convert graph to GeoDataFrame
            edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
            
            # Extract street segment information
            segments = []
            for idx, edge in edges.iterrows():
                segment = {
                    'id': idx,
                    'geometry': edge['geometry'],
                    'length': edge.get('length', 0),
                    'name': edge.get('name', 'Unknown'),
                    'highway': edge.get('highway', 'Unknown'),
                    'lanes': edge.get('lanes', 1),
                    'maxspeed': edge.get('maxspeed', 25),
                    'oneway': edge.get('oneway', False)
                }
                segments.append(segment)
            
            print(f"Extracted {len(segments)} street segments from network")
            return segments
            
        except Exception as e:
            print(f"Error extracting street segments: {e}")
            return []
    
    def parse_building_heights(self, buildings_data: List[Dict]) -> Dict[str, float]:
        """Parse building heights from ArcGIS data.
        
        Args:
            buildings_data: Raw building data from ArcGIS API
            
        Returns:
            Dictionary mapping building ID to height
        """
        building_heights = {}
        
        for building in buildings_data:
            try:
                # Extract building ID and height from ArcGIS format
                building_id = building.get('bin')
                height = building.get('height_roof')
                
                if building_id and height is not None:
                    # Convert height to float
                    try:
                        height_float = float(height)
                        if height_float > 0:  # Only include valid heights
                            building_heights[building_id] = height_float
                    except (ValueError, TypeError):
                        continue
                        
            except Exception as e:
                print(f"Error parsing building {building}: {e}")
                continue
                
        print(f"Parsed heights for {len(building_heights)} buildings")
        return building_heights
