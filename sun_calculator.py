"""
Sun position and shade calculation module.
Calculates sun angles and projects shadows based on building heights and tree coverage.
"""

import numpy as np
from datetime import datetime, time
from typing import Dict, List, Tuple, Optional
import logging
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union
import math

logger = logging.getLogger(__name__)

class SunCalculator:
    """Calculates sun positions and shade projections."""
    
    def __init__(self, latitude: float = 40.7128, longitude: float = -74.0060):
        """
        Initialize sun calculator for NYC coordinates.
        
        Args:
            latitude: Latitude in decimal degrees (NYC ≈ 40.7128)
            longitude: Longitude in decimal degrees (NYC ≈ -74.0060)
        """
        self.latitude = latitude
        self.longitude = longitude
        self.latitude_rad = math.radians(latitude)
        
        # NYC timezone offset (EST/EDT)
        self.timezone_offset = -5  # EST
        
    def calculate_sun_position(self, 
                             date: datetime,
                             time_of_day: time) -> Dict[str, float]:
        """
        Calculate sun position for given date and time.
        
        Args:
            date: Date to calculate for
            time_of_day: Time of day (local time)
            
        Returns:
            Dict with azimuth and elevation angles
        """
        try:
            # Convert to UTC
            utc_time = self._local_to_utc(date, time_of_day)
            
            # Calculate day of year
            day_of_year = utc_time.timetuple().tm_yday
            
            # Calculate solar declination
            declination = self._calculate_declination(day_of_year)
            
            # Calculate hour angle
            hour_angle = self._calculate_hour_angle(utc_time)
            
            # Calculate solar elevation
            elevation = self._calculate_elevation(declination, hour_angle)
            
            # Calculate solar azimuth
            azimuth = self._calculate_azimuth(declination, hour_angle, elevation)
            
            return {
                'elevation': elevation,  # degrees above horizon
                'azimuth': azimuth,      # degrees from north (clockwise)
                'declination': declination,
                'hour_angle': hour_angle
            }
            
        except Exception as e:
            logger.error(f"Error calculating sun position: {e}")
            raise
    
    def calculate_shade_projection(self,
                                 building_geometry: Polygon,
                                 building_height: float,
                                 sun_position: Dict[str, float]) -> Polygon:
        """
        Calculate shadow projection for a building.
        
        Args:
            building_geometry: Building footprint as Polygon
            building_height: Building height in meters
            sun_position: Sun position dict with elevation and azimuth
            
        Returns:
            Shadow polygon
        """
        try:
            elevation = sun_position['elevation']
            azimuth = sun_position['azimuth']
            
            # If sun is below horizon, no shadow
            if elevation <= 0:
                return Polygon()
            
            # Calculate shadow length based on sun elevation
            # Shadow length = height / tan(elevation)
            shadow_length = building_height / math.tan(math.radians(elevation))
            
            # Calculate shadow direction vector
            # Convert azimuth to radians (0 = North, 90 = East)
            azimuth_rad = math.radians(azimuth)
            
            # Calculate shadow offset
            dx = shadow_length * math.sin(azimuth_rad)
            dy = shadow_length * math.cos(azimuth_rad)
            
            # Create shadow by translating building footprint
            shadow = building_geometry.translate(dx, dy)
            
            # Union with original building to create complete shadow
            complete_shadow = unary_union([building_geometry, shadow])
            
            return complete_shadow
            
        except Exception as e:
            logger.error(f"Error calculating shade projection: {e}")
            return Polygon()
    
    def calculate_street_shade(self,
                             street_segment: LineString,
                             buildings: List[Tuple[Polygon, float]],
                             trees: List[Tuple[Point, float]],
                             sun_position: Dict[str, float]) -> float:
        """
        Calculate shade coverage for a street segment.
        
        Args:
            street_segment: Street geometry as LineString
            buildings: List of (geometry, height) tuples for buildings
            trees: List of (geometry, height) tuples for trees
            sun_position: Sun position dict
            
        Returns:
            Shade score from 0.0 (no shade) to 1.0 (fully shaded)
        """
        try:
            if sun_position['elevation'] <= 0:
                return 1.0  # Night time, fully shaded
            
            # Buffer street segment to create analysis area
            street_buffer = street_segment.buffer(10)  # 10 meter buffer
            
            total_shade_area = 0
            total_area = street_buffer.area
            
            # Calculate building shadows
            for building_geom, building_height in buildings:
                if building_geom.intersects(street_buffer):
                    shadow = self.calculate_shade_projection(
                        building_geom, building_height, sun_position
                    )
                    if shadow.intersects(street_buffer):
                        intersection = shadow.intersection(street_buffer)
                        total_shade_area += intersection.area
            
            # Calculate tree shadows (simplified as circular shadows)
            for tree_geom, tree_diameter in trees:
                if tree_geom.intersects(street_buffer):
                    # Estimate tree height from diameter (rough approximation)
                    tree_height = tree_diameter * 20  # 20x diameter is rough height
                    
                    shadow = self.calculate_shade_projection(
                        tree_geom.buffer(tree_diameter/2), tree_height, sun_position
                    )
                    if shadow.intersects(street_buffer):
                        intersection = shadow.intersection(street_buffer)
                        total_shade_area += intersection.area
            
            # Calculate shade percentage
            shade_score = min(1.0, total_shade_area / total_area)
            
            return shade_score
            
        except Exception as e:
            logger.error(f"Error calculating street shade: {e}")
            return 0.0
    
    def get_seasonal_shade_factors(self, date: datetime) -> Dict[str, float]:
        """
        Get seasonal shade factors based on date.
        
        Args:
            date: Date to calculate factors for
            
        Returns:
            Dict with seasonal factors
        """
        day_of_year = date.timetuple().tm_yday
        
        # Calculate seasonal factor (1.0 = summer solstice, 0.0 = winter solstice)
        # Approximate using cosine function
        seasonal_factor = 0.5 * (1 + math.cos(2 * math.pi * (day_of_year - 172) / 365))
        
        return {
            'summer_factor': seasonal_factor,
            'winter_factor': 1 - seasonal_factor,
            'day_of_year': day_of_year
        }
    
    def _local_to_utc(self, local_date: datetime, local_time: time) -> datetime:
        """Convert local time to UTC."""
        # Simplified conversion - in production, use pytz for proper timezone handling
        local_datetime = datetime.combine(local_date, local_time)
        utc_datetime = local_datetime.replace(hour=local_datetime.hour - self.timezone_offset)
        return utc_datetime
    
    def _calculate_declination(self, day_of_year: int) -> float:
        """Calculate solar declination angle."""
        # Simplified formula for solar declination
        declination = 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))
        return declination
    
    def _calculate_hour_angle(self, utc_time: datetime) -> float:
        """Calculate solar hour angle."""
        # Calculate time since solar noon (simplified)
        hour = utc_time.hour + utc_time.minute / 60.0
        hour_angle = 15 * (hour - 12)  # 15 degrees per hour
        return hour_angle
    
    def _calculate_elevation(self, declination: float, hour_angle: float) -> float:
        """Calculate solar elevation angle."""
        declination_rad = math.radians(declination)
        hour_angle_rad = math.radians(hour_angle)
        
        # Solar elevation formula
        sin_elevation = (math.sin(self.latitude_rad) * math.sin(declination_rad) + 
                        math.cos(self.latitude_rad) * math.cos(declination_rad) * 
                        math.cos(hour_angle_rad))
        
        elevation = math.degrees(math.asin(max(-1, min(1, sin_elevation))))
        return elevation
    
    def _calculate_azimuth(self, declination: float, hour_angle: float, elevation: float) -> float:
        """Calculate solar azimuth angle."""
        if elevation <= 0:
            return 0
        
        declination_rad = math.radians(declination)
        hour_angle_rad = math.radians(hour_angle)
        elevation_rad = math.radians(elevation)
        
        # Solar azimuth formula
        cos_azimuth = ((math.sin(declination_rad) * math.cos(self.latitude_rad) - 
                       math.cos(declination_rad) * math.sin(self.latitude_rad) * 
                       math.cos(hour_angle_rad)) / math.cos(elevation_rad))
        
        cos_azimuth = max(-1, min(1, cos_azimuth))
        azimuth = math.degrees(math.acos(cos_azimuth))
        
        # Adjust azimuth based on time of day
        if hour_angle > 0:  # Afternoon
            azimuth = 360 - azimuth
        
        return azimuth
