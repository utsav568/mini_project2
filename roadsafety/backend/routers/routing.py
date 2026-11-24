"""
roadsafety/backend/routers/routing.py
=====================================
Routing and nearest-facility locator endpoints using the Delhi NCR Road Network Graph.
"""

from fastapi import APIRouter
from ..schemas import RouteRequest, RouteResponse
from ..database import BASE_DIR

import sys
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from modules.routing_engine import GraphRoutingEngine

router = APIRouter(prefix="/api/routing", tags=["Smart Routing"])
_router_engine = GraphRoutingEngine(seed=42)


@router.post("/route", response_model=RouteResponse)
def compute_route(payload: RouteRequest):
    """
    Compute optimal road network route between coordinates using Dijkstra shortest path.
    Also returns the closest regional trauma center and evacuation route leg.
    """
    src_node = _router_engine.find_nearest_node(payload.source_lat, payload.source_lon)
    tgt_node = _router_engine.find_nearest_node(payload.dest_lat, payload.dest_lon)

    route_res = _router_engine.route(
        source_node=src_node,
        target_node=tgt_node,
        vehicle_type=payload.vehicle_type or "ambulance",
    )

    coords = [[lat, lon] for lat, lon in route_res.path_coords]
    src_label = _router_engine.get_node_label(src_node)
    tgt_label = _router_engine.get_node_label(tgt_node)

    return {
        "route_found": True,
        "path_nodes": route_res.path,
        "path_coords": coords,
        "total_distance_km": round(len(route_res.path) * 0.75, 2),
        "estimated_time_min": route_res.estimated_time_min,
        "source_label": src_label,
        "dest_label": tgt_label,
        "nearest_hospital": route_res.nearest_hospital,
    }


@router.get("/nearest-hospital")
def get_nearest_hospital(latitude: float, longitude: float):
    """Locate the nearest trauma hospital to given GPS coordinates."""
    node = _router_engine.find_nearest_node(latitude, longitude)
    hosp_data, route_nodes, eta = _router_engine.get_nearest_hospital(node)
    return {
        "hospital": hosp_data,
        "eta_min": eta,
        "route_nodes": route_nodes,
    }
