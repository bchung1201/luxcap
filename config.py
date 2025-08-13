"""
Configuration file for NYC Shade Routing project.
Contains API keys, constants, and settings.
"""

import os
from typing import Dict, Any

# NYC Data APIs
NYC_BUILDING_FOOTPRINTS_URL = "5zhs-2jue"  # Building footprints with heights
NYC_TREE_DATA_URL = "5rq2-4xqu"  # Tree data
NYC_PLUTO_URL = "64uk-42ks"  # PLUTO data
NYC_CSCL_URL = "inkn-q76z"  # CSCL street segments

# NYC Bounding Box (approximate)
NYC_BOUNDS = {
    "min_lat": 40.4774,
    "max_lat": 40.9176,
    "min_lon": -74.2591,
    "max_lon": -73.7004
}

# Sun calculation parameters
SUN_ANGLES = {
    "summer_solstice": 73.5,  # degrees at solar noon
    "winter_solstice": 26.5,  # degrees at solar noon
    "spring_equinox": 50.0,   # degrees at solar noon
    "fall_equinox": 50.0      # degrees at solar noon
}

# Shade scoring weights
SHADE_WEIGHTS = {
    "building_shade": 1.0,
    "tree_shade": 0.8,
    "time_of_day": 0.6,
    "season": 0.4
}

# Routing parameters
ROUTING_PARAMS = {
    "max_distance_km": 50.0,
    "shade_threshold": 0.3,  # minimum shade score to consider "shady"
    "time_weight": 0.4,      # weight for travel time vs shade
    "shade_weight": 0.6      # weight for shade vs travel time
}

# Modal configuration
MODAL_CONFIG = {
    "image": "python:3.11-slim",
    "memory": 8192,  # 8GB RAM
    "cpu": 2.0,      # 2 CPU cores
    "timeout": 3600  # 1 hour timeout
}

def get_api_keys() -> Dict[str, str]:
    """Get API keys from environment variables."""
    return {
        "mapbox_token": os.getenv("MAPBOX_TOKEN", ""),
        "nyc_data_token": os.getenv("NYC_DATA_TOKEN", ""),
    }

def validate_config() -> bool:
    """Validate that all required configuration is present."""
    api_keys = get_api_keys()
    
    # Check if we have at least one mapping service
    if not api_keys["mapbox_token"]:
        print("Warning: MAPBOX_TOKEN not set. Some features may be limited.")
    
    return True
