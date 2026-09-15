"use client";

import React, { useMemo } from "react";
import Link from "next/link";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Leaflet's default marker images don't bundle cleanly with Next.js's asset pipeline —
// point them at the CDN copy that matches the installed leaflet version instead.
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// India's rough geographic center — used when no task has coordinates yet.
const INDIA_CENTER = [22.5, 79.0];
const INDIA_ZOOM = 5;

function inr(min, max) {
  if (min == null) return null;
  return max && max !== min ? `₹${min}–₹${max}` : `₹${min}`;
}

/** Task markers on an OpenStreetMap view. Tasks without a resolvable PIN are skipped. */
export default function TaskMapView({ tasks = [] }) {
  const located = useMemo(() => tasks.filter((t) => t.latitude != null && t.longitude != null), [tasks]);

  const center = located.length > 0 ? [located[0].latitude, located[0].longitude] : INDIA_CENTER;
  const zoom = located.length > 0 ? 11 : INDIA_ZOOM;

  return (
    <div className="task-map-wrapper">
      <MapContainer center={center} zoom={zoom} scrollWheelZoom style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {located.map((task) => {
          const schema = task.task_schema || {};
          const price = schema.suggestedPriceRange || {};
          return (
            <Marker key={task.id} position={[task.latitude, task.longitude]}>
              <Popup>
                <div className="task-map-popup">
                  <strong>{schema.title || task.subcategory || "Task"}</strong>
                  <div className="task-map-popup-meta">
                    {task.category}
                    {inr(price.min, price.max) ? ` · ${inr(price.min, price.max)}` : ""}
                  </div>
                  <Link href={`/tasks/${task.id}`}>View details →</Link>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
      {tasks.length > 0 && located.length === 0 && (
        <p className="task-map-empty">None of these tasks have a recognizable PIN code to place on the map.</p>
      )}

      <style jsx>{`
        .task-map-wrapper { position: relative; height: 420px; border-radius: 12px; overflow: hidden; border: 1px solid var(--border-glow); }
        .task-map-empty { position: absolute; bottom: 10px; left: 10px; right: 10px; background: rgba(7,9,19,0.85); color: var(--color-text-muted); font-size: 0.78rem; padding: 8px 12px; border-radius: 8px; z-index: 1000; }
        :global(.task-map-popup) { display: flex; flex-direction: column; gap: 4px; font-size: 0.85rem; }
        :global(.task-map-popup-meta) { color: #64748b; font-size: 0.78rem; }
        :global(.task-map-popup a) { color: #0d9488; font-weight: 600; text-decoration: none; margin-top: 2px; }
      `}</style>
    </div>
  );
}
