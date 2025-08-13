"""
Modal app for NYC shade routing.
Handles remote computation of shade-aware routes.
"""

import modal
import os
from typing import Dict, List, Tuple, Optional
import logging
import tempfile
import json

# Import our modules
from data_fetchers import NYCDataFetcher
from sun_calculator import SunCalculator
from shade_router import ShadeRouter
from visualization import RouteVisualizer
from config import MODAL_CONFIG, validate_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Modal app
app = modal.App("nyc-shade-router")

# Create image with all dependencies
image = modal.Image.debian_slim().pip_install([
    "osmnx>=1.6.0",
    "geopandas>=0.14.0",
    "shapely>=2.0.0",
    "requests>=2.31.0",
    "folium>=0.15.0",
    "numpy>=1.24.0",
    "pandas>=2.0.0",
    "scipy>=1.11.0",
    "matplotlib>=3.7.0",
    "seaborn>=0.12.0",
    "pyproj>=3.6.0",
    "rtree>=1.1.0",
    "geopy>=2.4.0",
    "networkx>=3.0.0"
])

@app.function(
    image=image,
    memory=MODAL_CONFIG["memory"],
    cpu=MODAL_CONFIG["cpu"],
    timeout=MODAL_CONFIG["timeout"]
)
def fetch_nyc_data(center_point: Tuple[float, float], 
                   radius_meters: int = 5000,
                   building_limit: int = 10000,
                   tree_limit: int = 5000) -> Dict:
    """
    Fetch NYC data (street network, buildings, trees) remotely using Modal.
    
    Args:
        center_point: (lat, lon) center point for data fetching
        radius_meters: Radius to fetch street network within
        building_limit: Maximum number of buildings to fetch
        tree_limit: Maximum number of trees to fetch
        
    Returns:
        Dict with data summary and file paths
    """
    try:
        logger.info(f"Fetching NYC data for center point {center_point}")
        
        # Initialize data fetcher
        fetcher = NYCDataFetcher()
        
        # Fetch street network
        street_network = fetcher.fetch_street_network(center_point, radius_meters)
        
        # Fetch building footprints
        buildings = fetcher.fetch_building_footprints(limit=building_limit)
        
        # Fetch tree data
        trees = fetcher.fetch_tree_data(limit=tree_limit)
        
        # Get data summary
        summary = fetcher.get_data_summary()
        
        # Save data to temporary files for transfer
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            street_network.to_file(f.name, driver='GeoJSON')
            street_network_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            buildings.to_file(f.name, driver='GeoJSON')
            buildings_path = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            trees.to_file(f.name, driver='GeoJSON')
            trees_path = f.name
        
        return {
            'summary': summary,
            'street_network_path': street_network_path,
            'buildings_path': buildings_path,
            'trees_path': trees_path,
            'center_point': center_point,
            'radius_meters': radius_meters
        }
        
    except Exception as e:
        logger.error(f"Error fetching NYC data: {e}")
        raise

@app.function(
    image=image,
    memory=MODAL_CONFIG["memory"],
    cpu=MODAL_CONFIG["cpu"],
    timeout=MODAL_CONFIG["timeout"]
)
def calculate_shade_route(street_network_path: str,
                         buildings_path: str,
                         trees_path: str,
                         start_point: Tuple[float, float],
                         end_point: Tuple[float, float],
                         date: Optional[str] = None,
                         time_of_day: Optional[str] = None,
                         max_distance_km: Optional[float] = None) -> Dict:
    """
    Calculate shade-aware route remotely using Modal.
    
    Args:
        street_network_path: Path to street network GeoJSON file
        buildings_path: Path to buildings GeoJSON file
        trees_path: Path to trees GeoJSON file
        start_point: (lat, lon) starting point
        end_point: (lat, lon) ending point
        date: Date string (YYYY-MM-DD)
        time_of_day: Time string (HH:MM)
        max_distance_km: Maximum route distance in km
        
    Returns:
        Dict with route information
    """
    try:
        logger.info(f"Calculating shade route from {start_point} to {end_point}")
        
        # Load data from files
        import geopandas as gpd
        
        street_network = gpd.read_file(street_network_path)
        buildings = gpd.read_file(buildings_path)
        trees = gpd.read_file(trees_path)
        
        # Initialize components
        sun_calculator = SunCalculator()
        router = ShadeRouter(street_network, buildings, trees, sun_calculator)
        
        # Find route
        route_info = router.find_shadiest_route(
            start_point, end_point, date, time_of_day, max_distance_km
        )
        
        # Get route alternatives
        alternatives = router.get_route_alternatives(
            start_point, end_point, num_alternatives=3, date=date, time_of_day=time_of_day
        )
        
        return {
            'primary_route': route_info,
            'alternatives': alternatives,
            'data_summary': {
                'street_segments': len(street_network),
                'buildings': len(buildings),
                'trees': len(trees)
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating shade route: {e}")
        raise

@app.function(
    image=image,
    memory=MODAL_CONFIG["memory"],
    cpu=MODAL_CONFIG["cpu"],
    timeout=MODAL_CONFIG["timeout"]
)
def create_route_visualization(street_network_path: str,
                              buildings_path: str,
                              trees_path: str,
                              route_data: Dict,
                              output_filename: str = "shade_route_map.html") -> str:
    """
    Create route visualization remotely using Modal.
    
    Args:
        street_network_path: Path to street network GeoJSON file
        buildings_path: Path to buildings GeoJSON file
        trees_path: Path to trees GeoJSON file
        route_data: Route information from calculate_shade_route
        output_filename: Name for output HTML file
        
    Returns:
        Path to generated HTML file
    """
    try:
        logger.info("Creating route visualization")
        
        # Load data from files
        import geopandas as gpd
        
        street_network = gpd.read_file(street_network_path)
        buildings = gpd.read_file(buildings_path)
        trees = gpd.read_file(trees_path)
        
        # Initialize visualizer
        visualizer = RouteVisualizer()
        
        # Create base map
        center_lat = (route_data['primary_route']['start_point'][0] + 
                     route_data['primary_route']['end_point'][0]) / 2
        center_lon = (route_data['primary_route']['start_point'][1] + 
                     route_data['primary_route']['end_point'][1]) / 2
        
        map_obj = visualizer.create_base_map((center_lat, center_lon))
        
        # Add all routes to map
        all_routes = [route_data['primary_route']] + route_data['alternatives']
        map_obj = visualizer.add_multiple_routes(all_routes, map_obj)
        
        # Save map
        output_path = f"/tmp/{output_filename}"
        visualizer.save_map(map_obj, output_path)
        
        # Read file content for transfer
        with open(output_path, 'r') as f:
            html_content = f.read()
        
        return html_content
        
    except Exception as e:
        logger.error(f"Error creating route visualization: {e}")
        raise

@app.function(
    image=image,
    memory=MODAL_CONFIG["memory"],
    cpu=MODAL_CONFIG["cpu"],
    timeout=MODAL_CONFIG["timeout"]
)
def create_shade_analysis_plots(route_data: Dict) -> Dict:
    """
    Create shade analysis plots remotely using Modal.
    
    Args:
        route_data: Route information from calculate_shade_route
        
    Returns:
        Dict with plot data (base64 encoded)
    """
    try:
        logger.info("Creating shade analysis plots")
        
        import base64
        import io
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        
        from visualization import RouteVisualizer
        
        visualizer = RouteVisualizer()
        
        # Create plots for primary route
        fig = visualizer.create_shade_analysis_plot(route_data['primary_route'])
        
        # Convert plot to base64 string
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        plot_data = base64.b64encode(buffer.getvalue()).decode()
        
        # Create summary statistics
        primary_route = route_data['primary_route']
        alternatives = route_data['alternatives']
        
        summary_stats = {
            'primary_route': {
                'distance_km': primary_route['total_distance_km'],
                'avg_shade': primary_route['average_shade_score'],
                'segments': primary_route['num_segments']
            },
            'alternatives': [
                {
                    'distance_km': alt['total_distance_km'],
                    'avg_shade': alt['average_shade_score'],
                    'segments': alt['num_segments'],
                    'weights': alt.get('weight_combination', 'Default')
                }
                for alt in alternatives
            ]
        }
        
        return {
            'plot_data': plot_data,
            'summary_stats': summary_stats
        }
        
    except Exception as e:
        logger.error(f"Error creating shade analysis plots: {e}")
        raise

@app.local_entrypoint()
def main():
    """
    Main entry point for the Modal app.
    Demonstrates the complete shade routing workflow.
    """
    try:
        # Validate configuration
        if not validate_config():
            logger.warning("Configuration validation failed, but continuing...")
        
        # Example usage
        print("🚀 NYC Shade Router - Modal App")
        print("=" * 50)
        
        # Example coordinates in NYC (Times Square to Central Park)
        start_point = (40.7580, -73.9855)  # Times Square
        end_point = (40.7829, -73.9654)    # Central Park
        
        print(f"📍 Start: Times Square {start_point}")
        print(f"🎯 End: Central Park {end_point}")
        print(f"📅 Date: Today")
        print(f"⏰ Time: 2:00 PM")
        print()
        
        # Step 1: Fetch NYC data
        print("📊 Step 1: Fetching NYC data...")
        data_result = fetch_nyc_data.remote(
            center_point=start_point,
            radius_meters=3000,  # 3km radius
            building_limit=5000,
            tree_limit=2000
        )
        
        print(f"✅ Fetched {data_result['summary']['street_segments']} street segments")
        print(f"✅ Fetched {data_result['summary']['buildings']} buildings")
        print(f"✅ Fetched {data_result['summary']['trees']} trees")
        print()
        
        # Step 2: Calculate shade route
        print("🛣️  Step 2: Calculating shade-aware route...")
        route_result = calculate_shade_route.remote(
            street_network_path=data_result['street_network_path'],
            buildings_path=data_result['buildings_path'],
            trees_path=data_result['trees_path'],
            start_point=start_point,
            end_point=end_point,
            date="2024-07-15",  # Summer date
            time_of_day="14:00",  # 2:00 PM
            max_distance_km=5.0
        )
        
        primary_route = route_result['primary_route']
        print(f"✅ Found route: {primary_route['total_distance_km']:.2f} km")
        print(f"✅ Average shade: {primary_route['average_shade_score']:.2f}")
        print(f"✅ Route segments: {primary_route['num_segments']}")
        print()
        
        # Step 3: Create visualization
        print("🗺️  Step 3: Creating route visualization...")
        html_content = create_route_visualization.remote(
            street_network_path=data_result['street_network_path'],
            buildings_path=data_result['buildings_path'],
            trees_path=data_result['trees_path'],
            route_data=route_result,
            output_filename="nyc_shade_route.html"
        )
        
        # Save visualization locally
        with open("nyc_shade_route.html", "w") as f:
            f.write(html_content)
        
        print("✅ Saved route map to: nyc_shade_route.html")
        print()
        
        # Step 4: Create analysis plots
        print("📈 Step 4: Creating shade analysis plots...")
        plot_result = create_shade_analysis_plots.remote(route_result)
        
        # Save plot data
        import base64
        plot_data = base64.b64decode(plot_result['plot_data'])
        with open("shade_analysis.png", "wb") as f:
            f.write(plot_data)
        
        print("✅ Saved analysis plot to: shade_analysis.png")
        print()
        
        # Display summary
        print("📋 Route Summary:")
        print(f"   Primary Route: {primary_route['total_distance_km']:.2f} km, {primary_route['average_shade_score']:.2f} avg shade")
        
        for i, alt in enumerate(route_result['alternatives'][:2]):  # Show first 2 alternatives
            print(f"   Alternative {i+1}: {alt['total_distance_km']:.2f} km, {alt['average_shade_score']:.2f} avg shade")
        
        print()
        print("🎉 Shade routing complete! Open nyc_shade_route.html in your browser to view the route.")
        
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
