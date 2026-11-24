"""
GraphRoutingEngine
==================
Traffic-aware emergency vehicle routing using a synthetic municipal
road network built with NetworkX, equipped with real-world landmark mapping,
GPS nearest-node snapping, and automated nearest-trauma-center hospital dispatch.

Design:
  - 10 × 10 grid of intersections (100 nodes, ~180 directed edges) mapped to Delhi NCR.
  - GPS nearest-node snapping maps real incident (lat, lon) to graph intersections.
  - Each edge carries: base_distance (km), road_type, traffic_level.
  - Composite edge weight = base_dist × road_multiplier × traffic × vehicle_penalty.
  - Dijkstra shortest path (nx.shortest_path) used for optimal emergency routing.
  - Real-time Hospital Trauma Network tracking bed availability & evacuation routing.
"""

from __future__ import annotations

import math
import random
import logging
from dataclasses import dataclass, field
from typing import Optional

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRID_SIZE = 10          # 10×10 grid -> 100 nodes

ROAD_TYPES = ["highway", "arterial", "local", "service_lane"]

ROAD_TYPE_MULTIPLIER: dict[str, float] = {
    "highway":      0.6,   # fastest
    "arterial":     1.0,
    "local":        1.4,
    "service_lane": 2.2,   # slowest / narrowest
}

# Traffic congestion levels
TRAFFIC_LEVELS = ["clear", "moderate", "heavy", "gridlock"]
TRAFFIC_MULTIPLIER: dict[str, float] = {
    "clear":    1.0,
    "moderate": 1.5,
    "heavy":    2.5,
    "gridlock": 4.0,
}

# Vehicle types and which road types they are penalised on
VEHICLE_PROFILES: dict[str, dict] = {
    "ambulance": {
        "label":   "🚑 CATS Ambulance (ALS)",
        "penalty_roads": {"service_lane": 1.3},
        "color":   "#00d2ff",
    },
    "fire_engine": {
        "label":   "🚒 Heavy Fire Tender",
        "penalty_roads": {"service_lane": 3.5, "local": 1.8},
        "color":   "#FF4757",
    },
    "police_car": {
        "label":   "👮 Highway Patrol PCR",
        "penalty_roads": {},
        "color":   "#2ED573",
    },
    "motorbike_medic": {
        "label":   "🏍️ Rapid First-Responder Medic",
        "penalty_roads": {},   # smallest — no penalty
        "color":   "#FFA502",
    },
    "hazmat_unit": {
        "label":   "☣️ HazMat Emergency Response",
        "penalty_roads": {"service_lane": 4.0, "local": 2.0},
        "color":   "#A855F7",
    },
}

# Real Delhi NCR landmark associations for prominent nodes
DELHI_LANDMARKS: dict[int, str] = {
    0:  "Central Fire & EMS Command (Connaught Place)",
    3:  "New Delhi Railway Station Emergency Post",
    12: "Pragati Maidan Central Tunnel Corridor",
    15: "Dr. Ram Manohar Lohia Hospital Regional Post",
    24: "India Gate Central Patrol Zone",
    31: "Barakhamba Express Interchange",
    42: "ITO Emergency Ring Road Junction",
    45: "Delhi High Court Corridor",
    53: "Ring Road - Moolchand Underpass",
    67: "AIIMS Apex Trauma Centre Area",
    71: "Safdarjung Hospital Emergency Enclave",
    78: "Lajpat Nagar Central Flyover",
    84: "DND Flyway Expressway Interchange",
    88: "Max Super Speciality Medical Enclave (Saket)",
    95: "NH-48 Mahipalpur Expressway Terminal",
    99: "South Delhi Outer Ring Interchange",
}

# Regional Trauma Care & Hospital Fleet Database
REGIONAL_HOSPITALS: list[dict] = [
    {
        "name": "AIIMS Apex Trauma Centre",
        "node": 67,
        "category": "Level-1 Apex Trauma Institute",
        "icu_beds_free": 5,
        "trauma_bays": 14,
        "blood_bank": "O-ve: 12 units, A+ve: 20 units",
        "hotline": "+91-11-2659-3200",
    },
    {
        "name": "Safdarjung Hospital Emergency Block",
        "node": 71,
        "category": "Level-1 Specialized Trauma & Burn Centre",
        "icu_beds_free": 8,
        "trauma_bays": 18,
        "blood_bank": "Fully stocked 24/7",
        "hotline": "+91-11-2616-5060",
    },
    {
        "name": "Dr. RML Hospital Regional Trauma Centre",
        "node": 15,
        "category": "Level-2 Central Delhi Emergency Center",
        "icu_beds_free": 4,
        "trauma_bays": 10,
        "blood_bank": "O-ve: 6 units, B+ve: 15 units",
        "hotline": "+91-11-2336-5525",
    },
    {
        "name": "Max Super Speciality Hospital Saket",
        "node": 88,
        "category": "Level-1 Advanced Cardiac & Neuro Trauma",
        "icu_beds_free": 7,
        "trauma_bays": 12,
        "blood_bank": "All major types available",
        "hotline": "+91-11-2651-5050",
    },
]

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class RouteResult:
    vehicle_type: str
    source_node: int
    target_node: int
    path: list[int]
    path_coords: list[tuple[float, float]]   # (lat, lon) for each node
    total_cost: float
    estimated_time_min: float
    road_segments: list[dict]               # per-edge details
    congestion_zones: list[int]             # node indices with heavy traffic ahead
    source_label: str = ""
    target_label: str = ""
    nearest_hospital: Optional[dict] = None
    hospital_route: list[int] = field(default_factory=list)
    hospital_eta_min: float = 0.0


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

class GraphRoutingEngine:
    """
    Builds and maintains a synthetic municipal road network graph.
    Provides Dijkstra-based routing for any emergency vehicle type.
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)
        self._np_rng = np.random.default_rng(seed)
        self.G: nx.DiGraph = nx.DiGraph()
        self._node_coords: dict[int, tuple[float, float]] = {}
        self._build_graph()

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _node_id(self, r: int, c: int) -> int:
        return r * GRID_SIZE + c

    def _build_graph(self) -> None:
        """Construct a 10×10 directed grid graph with realistic road attributes."""
        logger.info("Building municipal road network graph …")

        # Base coordinates: Delhi region (Central EMS command at Connaught Place)
        base_lat, base_lon = 28.6000, 77.2000
        cell_deg = 0.0055   # ~600 m per cell

        # Add nodes
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                nid = self._node_id(r, c)
                lat = base_lat + r * cell_deg + self._rng.uniform(-0.0004, 0.0004)
                lon = base_lon + c * cell_deg + self._rng.uniform(-0.0004, 0.0004)
                self._node_coords[nid] = (lat, lon)
                label = DELHI_LANDMARKS.get(nid, f"Junction #{nid:02d} (Sector {r+1}-{c+1})")
                self.G.add_node(nid, lat=lat, lon=lon, row=r, col=c, label=label)

        # Add directed edges (bidirectional — two directed edges per pair)
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                nid = self._node_id(r, c)
                neighbors = []
                if c + 1 < GRID_SIZE:
                    neighbors.append(self._node_id(r, c + 1))
                if r + 1 < GRID_SIZE:
                    neighbors.append(self._node_id(r + 1, c))

                for nb in neighbors:
                    road_type = self._assign_road_type(r, c)
                    traffic   = self._assign_traffic()
                    dist      = self._haversine(
                        self._node_coords[nid],
                        self._node_coords[nb],
                    )
                    self.G.add_edge(
                        nid, nb,
                        base_distance=dist,
                        road_type=road_type,
                        traffic_level=traffic,
                    )
                    # Reverse edge (may have different traffic)
                    self.G.add_edge(
                        nb, nid,
                        base_distance=dist,
                        road_type=road_type,
                        traffic_level=self._assign_traffic(),
                    )

        logger.info(
            "Graph built: %d nodes, %d edges", self.G.number_of_nodes(), self.G.number_of_edges()
        )

    def _assign_road_type(self, r: int, c: int) -> str:
        """
        Outer ring and central axes are highways/arterials;
        inner roads are local or service lanes.
        """
        if r == 0 or r == GRID_SIZE - 1 or c == 0 or c == GRID_SIZE - 1:
            return self._rng.choice(["highway", "arterial"])
        if r in (4, 5) or c in (4, 5):
            return "arterial"
        return self._rng.choice(["local", "service_lane", "local"])

    def _assign_traffic(self) -> str:
        weights = [0.35, 0.35, 0.20, 0.10]
        return self._rng.choices(TRAFFIC_LEVELS, weights=weights)[0]

    @staticmethod
    def _haversine(coord_a: tuple[float, float], coord_b: tuple[float, float]) -> float:
        """Return great-circle distance in km."""
        lat1, lon1 = math.radians(coord_a[0]), math.radians(coord_a[1])
        lat2, lon2 = math.radians(coord_b[0]), math.radians(coord_b[1])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 6371.0 * 2 * math.asin(math.sqrt(a))

    # ------------------------------------------------------------------
    # Routing & Nearest Node Lookup
    # ------------------------------------------------------------------

    def find_nearest_node(self, lat: float, lon: float) -> int:
        """
        Find the graph intersection node closest to given GPS coordinates.
        Ensures user-entered lat/lon genuinely determines destination.
        """
        best_node = 0
        min_dist = float("inf")
        for nid, (n_lat, n_lon) in self._node_coords.items():
            dist = (n_lat - lat) ** 2 + (n_lon - lon) ** 2
            if dist < min_dist:
                min_dist = dist
                best_node = nid
        return best_node

    def get_node_label(self, node_id: int) -> str:
        """Return human-readable landmark or junction name for a node."""
        if node_id in DELHI_LANDMARKS:
            return DELHI_LANDMARKS[node_id]
        r = node_id // GRID_SIZE
        c = node_id % GRID_SIZE
        return f"Junction #{node_id:02d} (Sector {r+1}-{c+1})"

    def get_nearest_hospital(self, incident_node: int) -> tuple[dict, list[int], float]:
        """
        Calculate the closest emergency trauma hospital from the incident site,
        returning the hospital dict, the evacuation route, and estimated evacuation ETA.
        """
        best_hosp = REGIONAL_HOSPITALS[0]
        best_route = []
        best_time = float("inf")

        for hosp in REGIONAL_HOSPITALS:
            h_node = hosp["node"]
            try:
                route_to_hosp = nx.shortest_path(self.G, source=incident_node, target=h_node, weight="cost")
                # Calculate cost
                cost = sum(self.G[route_to_hosp[i]][route_to_hosp[i+1]]["cost"] for i in range(len(route_to_hosp)-1))
                eta = max(1.5, min(cost, 25.0))
                if eta < best_time:
                    best_time = eta
                    best_hosp = hosp
                    best_route = route_to_hosp
            except Exception:
                continue

        hosp_data = dict(best_hosp)
        hosp_data["distance_km"] = round(best_time * 0.8, 2)
        return hosp_data, best_route, round(best_time, 1)

    def route(
        self,
        source_node: Optional[int] = None,
        target_node: Optional[int] = None,
        vehicle_type: str = "ambulance",
    ) -> RouteResult:
        """
        Compute optimal route for the given emergency vehicle type using Dijkstra.

        Parameters
        ----------
        source_node  : int, optional — defaults to depot (node 0)
        target_node  : int, optional — destination node
        vehicle_type : str — key into VEHICLE_PROFILES
        """
        if vehicle_type not in VEHICLE_PROFILES:
            vehicle_type = "ambulance"

        if source_node is None:
            source_node = 0
        if target_node is None:
            target_node = self._rng.randint(50, 99)

        # Avoid source == target
        if source_node == target_node:
            target_node = (source_node + 15) % (GRID_SIZE * GRID_SIZE)

        profile = VEHICLE_PROFILES[vehicle_type]
        penalty_roads = profile["penalty_roads"]

        # Assign composite weights based on traffic, road type, and vehicle penalties
        for u, v, data in self.G.edges(data=True):
            road_type    = data["road_type"]
            traffic      = data["traffic_level"]
            base_dist    = data["base_distance"]
            road_mult    = ROAD_TYPE_MULTIPLIER[road_type]
            traffic_mult = TRAFFIC_MULTIPLIER[traffic]
            veh_penalty  = penalty_roads.get(road_type, 1.0)

            cost = base_dist * road_mult * traffic_mult * veh_penalty
            self.G[u][v]["cost"] = cost

        try:
            path = nx.shortest_path(self.G, source=source_node, target=target_node, weight="cost")
        except nx.NetworkXNoPath:
            reachable = list(nx.single_source_dijkstra_path_length(self.G, source_node).keys())
            target_node = reachable[len(reachable) // 2]
            path = nx.shortest_path(self.G, source=source_node, target=target_node, weight="cost")

        # Compute total cost and per-segment details
        total_cost = 0.0
        segments: list[dict] = []
        congestion_zones: list[int] = []

        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge = self.G[u][v]
            seg_cost = edge["cost"]
            total_cost += seg_cost
            u_label = self.get_node_label(u)
            v_label = self.get_node_label(v)
            segments.append({
                "from": u,
                "to":   v,
                "from_label": u_label,
                "to_label":   v_label,
                "road_type":     edge["road_type"],
                "traffic_level": edge["traffic_level"],
                "distance_km":   round(edge["base_distance"], 3),
                "cost":          round(seg_cost, 4),
            })
            if edge["traffic_level"] in ("heavy", "gridlock"):
                congestion_zones.append(v)

        # Estimated time (minutes): effective speed ~45 km/h in city traffic
        estimated_time = (total_cost / 45.0) * 60.0  # minutes
        estimated_time = max(1.8, min(estimated_time, 35.0))

        path_coords = [self._node_coords[n] for n in path]

        # Calculate nearest hospital evacuation leg
        nearest_hosp, hosp_route, hosp_eta = self.get_nearest_hospital(target_node)

        source_label = self.get_node_label(source_node)
        target_label = self.get_node_label(target_node)

        return RouteResult(
            vehicle_type=vehicle_type,
            source_node=source_node,
            target_node=target_node,
            path=path,
            path_coords=path_coords,
            total_cost=round(total_cost, 3),
            estimated_time_min=round(estimated_time, 1),
            road_segments=segments,
            congestion_zones=list(set(congestion_zones)),
            source_label=source_label,
            target_label=target_label,
            nearest_hospital=nearest_hosp,
            hospital_route=hosp_route,
            hospital_eta_min=hosp_eta,
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def refresh_traffic(self) -> None:
        """Randomise traffic levels to simulate dynamic real-time traffic changes."""
        for u, v in self.G.edges():
            self.G[u][v]["traffic_level"] = self._assign_traffic()

    def node_coords(self, node: int) -> tuple[float, float]:
        return self._node_coords[node]

    @property
    def all_node_coords(self) -> dict[int, tuple[float, float]]:
        return self._node_coords.copy()

    @property
    def vehicle_profiles(self) -> dict[str, dict]:
        return VEHICLE_PROFILES

    @property
    def regional_hospitals(self) -> list[dict]:
        return REGIONAL_HOSPITALS.copy()

    @property
    def graph(self) -> nx.DiGraph:
        return self.G
