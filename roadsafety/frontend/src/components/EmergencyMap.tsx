import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

interface EmergencyMapProps {
  center?: [number, number];
  zoom?: number;
  pickable?: boolean;
  onLocationSelect?: (lat: number, lon: number) => void;
  selectedLocation?: [number, number] | null;
  vehicles?: any[];
  hospitals?: any[];
  incidents?: any[];
  routeCoords?: [number, number][];
  height?: string;
}

export const EmergencyMap: React.FC<EmergencyMapProps> = ({
  center = [28.6139, 77.2090], // Delhi NCR center
  zoom = 12,
  pickable = false,
  onLocationSelect,
  selectedLocation,
  vehicles = [],
  hospitals = [],
  incidents = [],
  routeCoords = [],
  height = '350px',
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markerLayerRef = useRef<L.LayerGroup | null>(null);
  const routeLayerRef = useRef<L.Polyline | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center,
        zoom,
        zoomControl: true,
      });

      // Carto Dark Matter Tiles
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap',
        maxZoom: 19,
      }).addTo(map);

      const markerLayer = L.layerGroup().addTo(map);
      markerLayerRef.current = markerLayer;
      mapInstanceRef.current = map;

      if (pickable) {
        map.on('click', (e: L.LeafletMouseEvent) => {
          if (onLocationSelect) {
            onLocationSelect(e.latlng.lat, e.latlng.lng);
          }
        });
      }
    }

    return () => {
      // Map cleanup handled on unmount
    };
  }, []);

  // Update markers and route
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layer = markerLayerRef.current;
    if (!map || !layer) return;

    layer.clearLayers();

    // 1. Picked Location Marker
    if (selectedLocation) {
      const pinIcon = L.divIcon({
        className: 'custom-pin',
        html: `<div style="background:#ef4444; width:22px; height:22px; border-radius:50%; border:3px solid #fff; box-shadow:0 0 15px #ef4444; display:flex; align-items:center; justify-content:center; color:#fff; font-size:10px;">📍</div>`,
        iconSize: [22, 22],
        iconAnchor: [11, 11],
      });
      L.marker(selectedLocation, { icon: pinIcon })
        .bindPopup(`<b>Selected Incident Location</b><br>${selectedLocation[0].toFixed(5)}, ${selectedLocation[1].toFixed(5)}`)
        .addTo(layer);
    }

    // 2. Hospitals
    hospitals.forEach((h) => {
      const hospIcon = L.divIcon({
        className: 'hosp-pin',
        html: `<div style="background:#0284c7; width:28px; height:28px; border-radius:8px; border:2px solid #38bdf8; display:flex; align-items:center; justify-content:center; font-size:14px; box-shadow:0 0 10px rgba(56,189,248,0.5);">🏥</div>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });
      L.marker([h.latitude, h.longitude], { icon: hospIcon })
        .bindPopup(`<b>🏥 ${h.name}</b><br>ICU Beds: <b>${h.available_icu_beds}/${h.total_icu_beds}</b><br>Status: ${h.status}`)
        .addTo(layer);
    });

    // 3. Vehicles
    vehicles.forEach((v) => {
      const color = v.status === 'Available' ? '#10b981' : '#f59e0b';
      const vehIcon = L.divIcon({
        className: 'veh-pin',
        html: `<div style="background:${color}; width:24px; height:24px; border-radius:50%; border:2px solid #fff; display:flex; align-items:center; justify-content:center; font-size:12px; box-shadow:0 0 10px ${color};">🚑</div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });
      L.marker([v.current_lat, v.current_lon], { icon: vehIcon })
        .bindPopup(`<b>${v.label}</b><br>Callsign: <b>${v.callsign}</b><br>Status: <b>${v.status}</b><br>Crew: ${v.crew_lead}`)
        .addTo(layer);
    });

    // 4. Incidents
    incidents.forEach((i) => {
      const color = i.urgency_index >= 7.5 ? '#ef4444' : '#f97316';
      const incIcon = L.divIcon({
        className: 'inc-pin',
        html: `<div style="background:${color}; width:26px; height:26px; border-radius:50%; border:2px solid #fee2e2; display:flex; align-items:center; justify-content:center; font-size:12px; box-shadow:0 0 12px ${color};" class="sos-button-pulse">💥</div>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      });
      L.marker([i.latitude, i.longitude], { icon: incIcon })
        .bindPopup(`<b>🚨 ${i.incident_id}</b><br>${i.category}<br>Urgency: <b>${i.urgency_index.toFixed(2)}</b><br>Status: <b>${i.status}</b><br>Landmark: ${i.landmark}`)
        .addTo(layer);
    });

    // 5. Route Polyline
    if (routeLayerRef.current) {
      map.removeLayer(routeLayerRef.current);
      routeLayerRef.current = null;
    }
    if (routeCoords.length > 0) {
      const polyline = L.polyline(routeCoords, {
        color: '#00f0ff',
        weight: 5,
        opacity: 0.85,
        dashArray: '1, 8',
      }).addTo(map);
      routeLayerRef.current = polyline;
      map.fitBounds(polyline.getBounds(), { padding: [40, 40] });
    }
  }, [vehicles, hospitals, incidents, selectedLocation, routeCoords]);

  return (
    <div className="relative w-full rounded-xl overflow-hidden border border-slate-800" style={{ height }}>
      <div ref={mapContainerRef} className="w-full h-full" />
      {pickable && (
        <div className="absolute top-3 left-3 z-[1000] bg-slate-900/90 border border-cyan-500/30 px-3 py-1.5 rounded-lg text-xs text-cyan-400 font-mono backdrop-blur flex items-center gap-1.5 shadow-lg">
          <span>📍</span> Click anywhere on map to pin accident scene
        </div>
      )}
    </div>
  );
};
