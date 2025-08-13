#!/usr/bin/env python3
"""
Test script for ArcGIS building data API.
"""

import requests
import json

def test_arcgis_api():
    """Test the ArcGIS building data API."""
    
    # Base URL for the building service
    base_url = "https://services6.arcgis.com/yG5s3afENB5iO9fj/arcgis/rest/services/BUILDING_view/FeatureServer/0"
    
    print("Testing ArcGIS Building Data API...")
    print("=" * 50)
    
    # Test 1: Get service info
    print("\n1. Getting service information...")
    try:
        info_url = f"{base_url}?f=json"
        response = requests.get(info_url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Service name: {data.get('name', 'Unknown')}")
            print(f"Description: {data.get('description', 'No description')}")
            
            # Show available fields
            fields = data.get('fields', [])
            print(f"\nAvailable fields ({len(fields)}):")
            for field in fields[:10]:  # Show first 10 fields
                print(f"  {field.get('name', 'Unknown')}: {field.get('type', 'Unknown')}")
            
            if len(fields) > 10:
                print(f"  ... and {len(fields) - 10} more fields")
                
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Try to get a small sample of data
    print("\n2. Trying to get sample data...")
    try:
        # Try different query approaches
        query_urls = [
            f"{base_url}/query?where=1%3D1&outFields=*&f=json&resultRecordCount=1",
            f"{base_url}/query?where=OBJECTID%3E0&outFields=OBJECTID&f=json&resultRecordCount=1",
            f"{base_url}/query?where=1%3D1&outFields=OBJECTID&f=json&resultRecordCount=1"
        ]
        
        for i, query_url in enumerate(query_urls):
            print(f"\n  Trying query {i+1}:")
            response = requests.get(query_url)
            print(f"    Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'features' in data and data['features']:
                        feature = data['features'][0]
                        print(f"    Success! Got feature with {len(feature.get('attributes', {}))} attributes")
                        print(f"    Sample attributes: {list(feature.get('attributes', {}).keys())[:5]}")
                        break
                    else:
                        print(f"    Response: {response.text[:200]}")
                except:
                    print(f"    Response: {response.text[:200]}")
            else:
                print(f"    Error: {response.text[:200]}")
                
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Try to get buildings with actual field names
    print("\n3. Testing building data retrieval...")
    try:
        # First, let's see what fields are actually available
        print("  Checking available fields...")
        info_response = requests.get(f"{base_url}?f=json")
        if info_response.status_code == 200:
            info_data = info_response.json()
            fields = info_data.get('fields', [])
            
            # Look for fields that might contain coordinates
            coord_fields = []
            for field in fields:
                if 'LAT' in field.get('name', '').upper() or 'LON' in field.get('name', '').upper() or 'X' in field.get('name', '').upper() or 'Y' in field.get('name', '').upper():
                    coord_fields.append(field.get('name'))
            
            print(f"    Coordinate-like fields: {coord_fields}")
            
            # Try a simple query without coordinates first
            print("  Trying simple query...")
            simple_query = f"{base_url}/query?where=1%3D1&outFields=*&f=json&resultRecordCount=2"
            response = requests.get(simple_query)
            
            if response.status_code == 200:
                data = response.json()
                if 'features' in data and data['features']:
                    feature = data['features'][0]
                    attrs = feature.get('attributes', {})
                    print(f"    Success! Got feature with attributes: {list(attrs.keys())}")
                    
                    # Show the actual values
                    for key, value in list(attrs.items())[:10]:
                        print(f"      {key}: {value}")
                else:
                    print(f"    No features in response: {response.text[:200]}")
            else:
                print(f"    Query failed: {response.text[:200]}")
                
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 50)
    print("Testing complete!")

if __name__ == "__main__":
    test_arcgis_api()
