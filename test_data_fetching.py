#!/usr/bin/env python3
"""
Test script for NYC data fetching functionality.
"""

import os
from data_fetchers import NYCDataFetcher

def test_nyc_data_fetching():
    """Test the NYC data fetching functionality."""
    
    # Initialize the fetcher
    fetcher = NYCDataFetcher()
    
    # Test location (Central Park area)
    test_lat, test_lon = 40.7812, -73.9665
    
    print("Testing NYC Data Fetcher...")
    print("=" * 50)
    
    # Test 1: Fetch buildings
    print("\n1. Testing building data fetch...")
    try:
        buildings = fetcher.fetch_buildings_near_location(test_lat, test_lon, radius_meters=2000, limit=100)
        if buildings:
            print(f"✓ Successfully fetched {len(buildings)} buildings")
            # Show sample building data
            if len(buildings) > 0:
                sample = buildings[0]
                print(f"   Sample building: BIN {sample.get('bin', 'No BIN')}, Height: {sample.get('height_roof', 'Unknown')}")
        else:
            print("✗ No buildings fetched")
    except Exception as e:
        print(f"✗ Error fetching buildings: {e}")
    
    # Test 2: Fetch street segments from OSMnx network
    print("\n2. Testing street segment extraction from OSMnx network...")
    try:
        # First get the street network
        network = fetcher.fetch_street_network(test_lat, test_lon, radius_km=1.0)
        if network:
            # Extract street segments from the network
            segments = fetcher.get_street_segments_from_network(network)
            if segments:
                print(f"✓ Successfully extracted {len(segments)} street segments from network")
                # Show sample segment data
                if len(segments) > 0:
                    sample = segments[0]
                    print(f"   Sample segment: {sample.get('name', 'No name')}, Length: {sample.get('length', 'Unknown'):.0f}m")
            else:
                print("✗ No street segments extracted")
        else:
            print("✗ No street network to extract segments from")
    except Exception as e:
        print(f"✗ Error extracting street segments: {e}")
    
    # Test 3: Fetch street network
    print("\n3. Testing street network fetch...")
    try:
        network = fetcher.fetch_street_network(test_lat, test_lon, radius_km=1.0)
        if network:
            print(f"✓ Successfully fetched street network with {len(network.nodes)} nodes and {len(network.edges)} edges")
        else:
            print("✗ No street network fetched")
    except Exception as e:
        print(f"✗ Error fetching street network: {e}")
    
    print("\n" + "=" * 50)
    print("Testing complete!")

if __name__ == "__main__":
    test_nyc_data_fetching()
