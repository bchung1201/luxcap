"""
Shade-aware routing module.
Finds the shadiest path between two points using modified shortest path algorithms.
"""

import networkx as nx
import geopandas as gpd
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from shapely.geometry import Point, LineString
from shapely.ops import nearest_points
import osmnx as ox

from sun_calculator import SunCalculator
from config import ROUTING_PARAMS, SHADE_WEIGHTS

logger = logging.getLogger(__name__)

class ShadeRouter:
    """Routes between points while maximizing shade coverage."""
    
    def __init__(self, 
                 street_network: gpd.GeoDataFrame,
                 buildings: gpd.GeoDataFrame,
                 trees: gpd.GeoDataFrame,
                 sun_calculator: SunCalculator):
        """
        Initialize shade router.
        
        Args:
            street_network: GeoDataFrame with street segments
            buildings: GeoDataFrame with building footprints and heights
            trees: GeoDataFrame with tree locations and diameters
            sun_calculator: SunCalculator instance
        """
        self.street_network = street_network
        self.buildings = buildings
        self.trees = trees
        self.sun_calculator = sun_calculator
        
        # Create NetworkX graph for routing
        self.graph = self._create_routing_graph()
        
        # Pre-process shade data for efficiency
        self._preprocess_shade_data()
    
    def _create_routing_graph(self) -> nx.Graph:
        """Create NetworkX graph from street network."""
        try:
            logger.info("Creating routing graph from street network")
            
            G = nx.Graph()
            
            for idx, row in self.street_network.iterrows():
                if row['geometry'].is_valid and not row['geometry'].is_empty:
                    # Get start and end points of street segment
                    coords = list(row['geometry'].coords)
                    if len(coords) >= 2:
                        start_point = coords[0]
                        end_point = coords[-1]
                        
                        # Add nodes and edge
                        G.add_node(start_point, pos=start_point)
                        G.add_node(end_point, pos=end_point)
                        
                        # Add edge with length as weight
                        length = row.get('length_m', 100)  # Default 100m if no length
                        G.add_edge(start_point, end_point, 
                                 length=length, 
                                 geometry=row['geometry'],
                                 original_idx=idx)
            
            logger.info(f"Created graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
            return G
            
        except Exception as e:
            logger.error(f"Error creating routing graph: {e}")
            raise
    
    def _preprocess_shade_data(self):
        """Pre-process shade data for efficient lookup."""
        try:
            logger.info("Pre-processing shade data")
            
            # Convert to lists for faster iteration
            self.building_list = []
            if not self.buildings.empty:
                for _, row in self.buildings.iterrows():
                    if row['geometry'].is_valid:
                        self.building_list.append((row['geometry'], row['height']))
            
            self.tree_list = []
            if not self.trees.empty:
                for _, row in self.trees.iterrows():
                    if row['geometry'].is_valid:
                        self.tree_list.append((row['geometry'], row['diameter']))
            
            logger.info(f"Pre-processed {len(self.building_list)} buildings and {len(self.tree_list)} trees")
            
        except Exception as e:
            logger.error(f"Error pre-processing shade data: {e}")
            raise
    
    def find_shadiest_route(self,
                           start_point: Tuple[float, float],
                           end_point: Tuple[float, float],
                           date: Optional[str] = None,
                           time_of_day: Optional[str] = None,
                           max_distance_km: Optional[float] = None) -> Dict:
        """
        Find the shadiest route between two points.
        
        Args:
            start_point: (lat, lon) starting point
            end_point: (lat, lon) ending point
            date: Date string (YYYY-MM-DD) or None for current date
            time_of_day: Time string (HH:MM) or None for current time
            max_distance_km: Maximum route distance in km
            
        Returns:
            Dict with route information including path, shade score, and metrics
        """
        try:
            logger.info(f"Finding shadiest route from {start_point} to {end_point}")
            
            # Parse date and time
            if date is None:
                from datetime import date as dt_date
                date = dt_date.today()
            else:
                from datetime import datetime
                date = datetime.strptime(date, "%Y-%m-%d").date()
            
            if time_of_day is None:
                from datetime import time
                time_of_day = time(12, 0)  # Default to noon
            else:
                from datetime import datetime
                time_of_day = datetime.strptime(time_of_day, "%H:%M").time()
            
            # Calculate sun position
            sun_position = self.sun_calculator.calculate_sun_position(date, time_of_day)
            logger.info(f"Sun position: elevation={sun_position['elevation']:.1f}°, azimuth={sun_position['azimuth']:.1f}°")
            
            # Find nearest nodes in graph
            start_node = self._find_nearest_node(start_point)
            end_node = self._find_nearest_node(end_point)
            
            if start_node is None or end_node is None:
                raise ValueError("Could not find start or end point in street network")
            
            # Calculate shade scores for all edges
            self._calculate_edge_shade_scores(sun_position)
            
            # Find optimal route
            route_info = self._find_optimal_route(start_node, end_node, max_distance_km)
            
            # Add metadata
            route_info.update({
                'start_point': start_point,
                'end_point': end_point,
                'date': date.strftime("%Y-%m-%d"),
                'time_of_day': time_of_day.strftime("%H:%M"),
                'sun_position': sun_position,
                'total_distance_km': route_info['total_distance'] / 1000,
                'average_shade_score': np.mean([edge['shade_score'] for edge in route_info['edges']])
            })
            
            logger.info(f"Found route with {route_info['total_distance']:.0f}m distance and {route_info['average_shade_score']:.2f} average shade")
            
            return route_info
            
        except Exception as e:
            logger.error(f"Error finding shadiest route: {e}")
            raise
    
    def _find_nearest_node(self, point: Tuple[float, float]) -> Optional[Tuple[float, float]]:
        """Find the nearest node in the graph to a given point."""
        try:
            # Convert lat,lon to lon,lat for consistency
            point_lon_lat = (point[1], point[0])
            
            min_distance = float('inf')
            nearest_node = None
            
            for node in self.graph.nodes():
                node_lon_lat = node
                distance = self._haversine_distance(point_lon_lat, node_lon_lat)
                
                if distance < min_distance:
                    min_distance = distance
                    nearest_node = node
            
            if nearest_node and min_distance < 1000:  # Within 1km
                return nearest_node
            else:
                logger.warning(f"No nearby nodes found for point {point}")
                return None
                
        except Exception as e:
            logger.error(f"Error finding nearest node: {e}")
            return None
    
    def _calculate_edge_shade_scores(self, sun_position: Dict[str, float]):
        """Calculate shade scores for all edges in the graph."""
        try:
            logger.info("Calculating shade scores for all edges")
            
            for edge in self.graph.edges(data=True):
                edge_data = edge[2]
                geometry = edge_data['geometry']
                
                # Calculate shade score for this edge
                shade_score = self.sun_calculator.calculate_street_shade(
                    geometry, self.building_list, self.tree_list, sun_position
                )
                
                # Store shade score in edge data
                edge_data['shade_score'] = shade_score
                
                # Calculate combined weight (lower is better for shortest path)
                # We want to minimize (1 - shade_score) * length
                shade_weight = ROUTING_PARAMS['shade_weight']
                time_weight = ROUTING_PARAMS['time_weight']
                
                # Normalize shade score to 0-1 range where 1 is best
                normalized_shade = shade_score
                
                # Combined weight: balance between shade and distance
                combined_weight = (time_weight * edge_data['length'] + 
                                 shade_weight * (1 - normalized_shade) * edge_data['length'])
                
                edge_data['combined_weight'] = combined_weight
            
            logger.info("Finished calculating shade scores")
            
        except Exception as e:
            logger.error(f"Error calculating edge shade scores: {e}")
            raise
    
    def _find_optimal_route(self, 
                           start_node: Tuple[float, float],
                           end_node: Tuple[float, float],
                           max_distance_km: Optional[float] = None) -> Dict:
        """Find optimal route using modified Dijkstra's algorithm."""
        try:
            logger.info(f"Finding optimal route from {start_node} to {end_node}")
            
            # Use NetworkX shortest path with combined weight
            try:
                path = nx.shortest_path(
                    self.graph, 
                    start_node, 
                    end_node, 
                    weight='combined_weight'
                )
            except nx.NetworkXNoPath:
                # Fallback to length-based routing if no path found
                logger.warning("No path found with combined weights, falling back to length-based routing")
                path = nx.shortest_path(
                    self.graph, 
                    start_node, 
                    end_node, 
                    weight='length'
                )
            
            # Calculate route metrics
            total_distance = 0
            total_shade_score = 0
            edges_info = []
            
            for i in range(len(path) - 1):
                start_n = path[i]
                end_n = path[i + 1]
                
                edge_data = self.graph[start_n][end_n]
                distance = edge_data['length']
                shade_score = edge_data.get('shade_score', 0.0)
                
                total_distance += distance
                total_shade_score += shade_score
                
                edges_info.append({
                    'start': start_n,
                    'end': end_n,
                    'distance_m': distance,
                    'shade_score': shade_score,
                    'geometry': edge_data['geometry']
                })
            
            # Check distance constraint
            if max_distance_km and (total_distance / 1000) > max_distance_km:
                logger.warning(f"Route distance {total_distance/1000:.1f}km exceeds maximum {max_distance_km}km")
            
            return {
                'path': path,
                'edges': edges_info,
                'total_distance': total_distance,
                'total_shade_score': total_shade_score,
                'num_segments': len(edges_info)
            }
            
        except Exception as e:
            logger.error(f"Error finding optimal route: {e}")
            raise
    
    def _haversine_distance(self, point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """Calculate Haversine distance between two points."""
        try:
            lon1, lat1 = point1
            lon2, lat2 = point2
            
            # Convert to radians
            lat1_rad = np.radians(lat1)
            lat2_rad = np.radians(lat2)
            delta_lat = np.radians(lat2 - lat1)
            delta_lon = np.radians(lon2 - lon1)
            
            # Haversine formula
            a = (np.sin(delta_lat / 2) ** 2 + 
                 np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2) ** 2)
            c = 2 * np.arcsin(np.sqrt(a))
            
            # Earth radius in meters
            earth_radius = 6371000
            
            return earth_radius * c
            
        except Exception as e:
            logger.error(f"Error calculating Haversine distance: {e}")
            return float('inf')
    
    def get_route_alternatives(self,
                              start_point: Tuple[float, float],
                              end_point: Tuple[float, float],
                              num_alternatives: int = 3,
                              date: Optional[str] = None,
                              time_of_day: Optional[str] = None) -> List[Dict]:
        """
        Get multiple route alternatives with different shade/distance trade-offs.
        
        Args:
            start_point: Starting point (lat, lon)
            end_point: Ending point (lat, lon)
            num_alternatives: Number of alternative routes to find
            date: Date string (YYYY-MM-DD)
            time_of_day: Time string (HH:MM)
            
        Returns:
            List of route alternatives
        """
        try:
            logger.info(f"Finding {num_alternatives} route alternatives")
            
            # Find primary route
            primary_route = self.find_shadiest_route(start_point, end_point, date, time_of_day)
            
            alternatives = [primary_route]
            
            # Find alternative routes with different weight combinations
            weight_combinations = [
                (0.8, 0.2),  # More emphasis on shade
                (0.2, 0.8),  # More emphasis on distance
                (0.5, 0.5),  # Balanced
            ]
            
            for shade_w, time_w in weight_combinations[:num_alternatives-1]:
                # Temporarily modify weights
                original_shade_weight = ROUTING_PARAMS['shade_weight']
                original_time_weight = ROUTING_PARAMS['time_weight']
                
                ROUTING_PARAMS['shade_weight'] = shade_w
                ROUTING_PARAMS['time_weight'] = time_w
                
                try:
                    # Recalculate edge weights and find route
                    start_node = self._find_nearest_node(start_point)
                    end_node = self._find_nearest_node(end_point)
                    
                    if start_node and end_node:
                        self._calculate_edge_shade_scores(primary_route['sun_position'])
                        alt_route = self._find_optimal_route(start_node, end_node)
                        
                        # Add metadata
                        alt_route.update({
                            'start_point': start_point,
                            'end_point': end_point,
                            'date': primary_route['date'],
                            'time_of_day': primary_route['time_of_day'],
                            'sun_position': primary_route['sun_position'],
                            'total_distance_km': alt_route['total_distance'] / 1000,
                            'average_shade_score': np.mean([edge['shade_score'] for edge in alt_route['edges']]),
                            'weight_combination': f"shade:{shade_w:.1f}, time:{time_w:.1f}"
                        })
                        
                        alternatives.append(alt_route)
                
                finally:
                    # Restore original weights
                    ROUTING_PARAMS['shade_weight'] = original_shade_weight
                    ROUTING_PARAMS['time_weight'] = original_time_weight
            
            # Sort alternatives by average shade score
            alternatives.sort(key=lambda x: x['average_shade_score'], reverse=True)
            
            logger.info(f"Found {len(alternatives)} route alternatives")
            return alternatives
            
        except Exception as e:
            logger.error(f"Error finding route alternatives: {e}")
            raise
