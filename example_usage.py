"""
Example usage of NYC Shade Router system.
This script demonstrates how to use the system locally without Modal.
"""

import logging
from datetime import datetime, time
from typing import Tuple

from data_fetchers import NYCDataFetcher
from sun_calculator import SunCalculator
from shade_router import ShadeRouter
from visualization import RouteVisualizer
from config import validate_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_local_example():
    """Run the shade routing example locally."""
    try:
        print("🚀 NYC Shade Router - Local Example")
        print("=" * 50)
        
        # Validate configuration
        if not validate_config():
            logger.warning("Configuration validation failed, but continuing...")
        
        # Example coordinates in NYC (Times Square to Central Park)
        start_point = (40.7580, -73.9855)  # Times Square
        end_point = (40.7829, -73.9654)    # Central Park
        
        print(f"📍 Start: Times Square {start_point}")
        print(f"🎯 End: Central Park {end_point}")
        print(f"📅 Date: July 15, 2024 (Summer)")
        print(f"⏰ Time: 2:00 PM")
        print()
        
        # Step 1: Fetch NYC data
        print("📊 Step 1: Fetching NYC data...")
        fetcher = NYCDataFetcher()
        
        # Fetch street network (smaller radius for local testing)
        street_network = fetcher.fetch_street_network(
            center_point=start_point,
            radius_meters=2000  # 2km radius for faster local processing
        )
        
        # Fetch building footprints
        buildings = fetcher.fetch_building_footprints(limit=2000)
        
        # Fetch tree data
        trees = fetcher.fetch_tree_data(limit=1000)
        
        print(f"✅ Fetched {len(street_network)} street segments")
        print(f"✅ Fetched {len(buildings)} buildings")
        print(f"✅ Fetched {len(trees)} trees")
        print()
        
        # Step 2: Initialize components
        print("🔧 Step 2: Initializing routing components...")
        sun_calculator = SunCalculator()
        router = ShadeRouter(street_network, buildings, trees, sun_calculator)
        
        print("✅ Sun calculator initialized")
        print("✅ Shade router initialized")
        print()
        
        # Step 3: Calculate shade route
        print("🛣️  Step 3: Calculating shade-aware route...")
        route_info = router.find_shadiest_route(
            start_point=start_point,
            end_point=end_point,
            date="2024-07-15",
            time_of_day="14:00",
            max_distance_km=3.0
        )
        
        print(f"✅ Found route: {route_info['total_distance_km']:.2f} km")
        print(f"✅ Average shade: {route_info['average_shade_score']:.2f}")
        print(f"✅ Route segments: {route_info['num_segments']}")
        print()
        
        # Step 4: Get route alternatives
        print("🔄 Step 4: Finding route alternatives...")
        alternatives = router.get_route_alternatives(
            start_point=start_point,
            end_point=end_point,
            num_alternatives=3,
            date="2024-07-15",
            time_of_day="14:00"
        )
        
        print(f"✅ Found {len(alternatives)} route alternatives")
        print()
        
        # Step 5: Create visualization
        print("🗺️  Step 5: Creating route visualization...")
        visualizer = RouteVisualizer()
        
        # Create base map
        center_lat = (start_point[0] + end_point[0]) / 2
        center_lon = (start_point[1] + end_point[1]) / 2
        map_obj = visualizer.create_base_map((center_lat, center_lon))
        
        # Add all routes to map
        all_routes = [route_info] + alternatives
        map_obj = visualizer.add_multiple_routes(all_routes, map_obj)
        
        # Save map
        output_filename = "nyc_shade_route_local.html"
        visualizer.save_map(map_obj, output_filename)
        
        print(f"✅ Saved route map to: {output_filename}")
        print()
        
        # Step 6: Create analysis plots
        print("📈 Step 6: Creating shade analysis plots...")
        fig = visualizer.create_shade_analysis_plot(route_info)
        
        # Save plot
        plot_filename = "shade_analysis_local.png"
        fig.savefig(plot_filename, dpi=150, bbox_inches='tight')
        print(f"✅ Saved analysis plot to: {plot_filename}")
        print()
        
        # Step 7: Display results
        print("📋 Route Summary:")
        print(f"   Primary Route: {route_info['total_distance_km']:.2f} km, {route_info['average_shade_score']:.2f} avg shade")
        
        for i, alt in enumerate(alternatives[:3]):  # Show all alternatives
            print(f"   Alternative {i+1}: {alt['total_distance_km']:.2f} km, {alt['average_shade_score']:.2f} avg shade")
            if 'weight_combination' in alt:
                print(f"           Weights: {alt['weight_combination']}")
        
        print()
        print("🎉 Local shade routing complete!")
        print(f"📁 Files created:")
        print(f"   - {output_filename} (interactive route map)")
        print(f"   - {plot_filename} (shade analysis plot)")
        print()
        print("💡 Open the HTML file in your browser to view the interactive route map!")
        
        return route_info, alternatives
        
    except Exception as e:
        logger.error(f"Error in local example: {e}")
        print(f"❌ Error: {e}")
        return None, None

def run_custom_route_example():
    """Run a custom route example with different parameters."""
    try:
        print("\n" + "="*60)
        print("🔄 Custom Route Example")
        print("="*60)
        
        # Custom coordinates (Brooklyn Bridge to Prospect Park)
        start_point = (40.7061, -73.9969)  # Brooklyn Bridge
        end_point = (40.6602, -73.9690)    # Prospect Park
        
        print(f"📍 Start: Brooklyn Bridge {start_point}")
        print(f"🎯 End: Prospect Park {end_point}")
        print(f"📅 Date: December 21, 2024 (Winter Solstice)")
        print(f"⏰ Time: 10:00 AM")
        print()
        
        # Initialize components
        fetcher = NYCDataFetcher()
        street_network = fetcher.fetch_street_network(
            center_point=start_point,
            radius_meters=3000
        )
        buildings = fetcher.fetch_building_footprints(limit=3000)
        trees = fetcher.fetch_tree_data(limit=1500)
        
        sun_calculator = SunCalculator()
        router = ShadeRouter(street_network, buildings, trees, sun_calculator)
        
        # Calculate route for winter morning
        route_info = router.find_shadiest_route(
            start_point=start_point,
            end_point=end_point,
            date="2024-12-21",
            time_of_day="10:00",
            max_distance_km=4.0
        )
        
        print(f"✅ Winter morning route: {route_info['total_distance_km']:.2f} km")
        print(f"✅ Average shade: {route_info['average_shade_score']:.2f}")
        print()
        
        # Compare with summer afternoon
        summer_route = router.find_shadiest_route(
            start_point=start_point,
            end_point=end_point,
            date="2024-07-15",
            time_of_day="14:00",
            max_distance_km=4.0
        )
        
        print(f"✅ Summer afternoon route: {summer_route['total_distance_km']:.2f} km")
        print(f"✅ Average shade: {summer_route['average_shade_score']:.2f}")
        print()
        
        # Create visualization
        visualizer = RouteVisualizer()
        center_lat = (start_point[0] + end_point[0]) / 2
        center_lon = (start_point[1] + end_point[1]) / 2
        map_obj = visualizer.create_base_map((center_lat, center_lon))
        
        # Add both routes
        map_obj = visualizer.add_route_to_map(route_info, map_obj, "Winter Morning (10 AM)")
        map_obj = visualizer.add_route_to_map(summer_route, map_obj, "Summer Afternoon (2 PM)")
        
        # Save comparison map
        comparison_filename = "seasonal_comparison.html"
        visualizer.save_map(map_obj, comparison_filename)
        
        print(f"✅ Saved seasonal comparison map to: {comparison_filename}")
        
        return route_info, summer_route
        
    except Exception as e:
        logger.error(f"Error in custom route example: {e}")
        print(f"❌ Error: {e}")
        return None, None

def main():
    """Main function to run examples."""
    try:
        # Run local example
        route_info, alternatives = run_local_example()
        
        if route_info:
            # Run custom route example
            winter_route, summer_route = run_custom_route_example()
            
            print("\n" + "="*60)
            print("📊 Final Summary")
            print("="*60)
            print("All examples completed successfully!")
            print("Check the generated HTML files for interactive route maps.")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Example interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
