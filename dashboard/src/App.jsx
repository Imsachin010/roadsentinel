import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, Circle, Marker, Polyline, Popup } from "react-leaflet";
import L from "leaflet";
import { io } from "socket.io-client";
import "leaflet/dist/leaflet.css";
import "./App.css";

const socket = io("http://localhost:5000");

function App() {
  const [vehicles, setVehicles] = useState({});
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    socket.on("telemetry_update", (frame) => {
      setVehicles((prev) => {
        const next = { ...prev };
        frame.forEach((v) => {
          next[v.vehicle_id] = { ...next[v.vehicle_id], ...v };
        });
        return next;
      });
    });

    socket.on("wrong_way_alert", (data) => {
      setAlerts((prev) => [data, ...prev].slice(0, 50));
      
      setVehicles((prev) => ({
        ...prev,
        [data.vehicle_id]: {
          ...prev[data.vehicle_id],
          ...data,
          isAlert: true
        }
      }));
    });

    return () => {
      socket.off("telemetry_update");
      socket.off("wrong_way_alert");
    };
  }, []);

  const createIcon = (heading, isAlert) => {
    // Offset by 90 deg mostly because standard arrow points right ➤
    const rotation = (heading || 0) - 90;
    return L.divIcon({
      html: `<div class="vehicle-arrow ${isAlert ? 'alerted' : 'normal'}" style="transform: rotate(${rotation}deg);">➤</div>`,
      className: "custom-div-icon",
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });
  };

  return (
    <div className="cockpit">
      <div className="map-pane">
        <MapContainer center={[13.0827, 80.2707]} zoom={13} style={{ height: "100%", width: "100%" }}>
          <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" />

          {Object.values(vehicles).map((v) => (
            <React.Fragment key={v.vehicle_id}>
              <Marker
                position={[v.lat, v.lon]}
                icon={createIcon(v.heading, v.isAlert)}
              >
                <Popup>Vehicle {v.vehicle_id} <br/> Speed: {v.speed?.toFixed(1)} m/s</Popup>
              </Marker>
              
              {v.isAlert && (
                <Circle
                  center={[v.lat, v.lon]}
                  radius={200}
                  pathOptions={{ color: '#f43f5e', fillColor: '#f43f5e', fillOpacity: 0.2, weight: 1 }}
                />
              )}

              {v.isAlert && v.collision_warning && vehicles[v.collision_warning.target_id] && (
                <Polyline
                  positions={[
                    [v.lat, v.lon],
                    [vehicles[v.collision_warning.target_id].lat, vehicles[v.collision_warning.target_id].lon]
                  ]}
                  pathOptions={{ color: '#eab308', weight: 3, dashArray: '8, 8' }}
                />
              )}
            </React.Fragment>
          ))}
        </MapContainer>
      </div>

      <div className="side-pane">
        <header className="header">
          <h1>🚨 Sentinel</h1>
          <p className="subtitle">Connected Cockpit Hub</p>
          <div className="status-indicator">
            <span className="dot pulse"></span> Telemetry Active
          </div>
        </header>

        <main className="alerts-container">
          {alerts.length === 0 ? (
            <div className="empty-state">No anomalies detected. Traffic flow nominal.</div>
          ) : (
            alerts.map((a, i) => (
              <div key={i} className={`alert-card fade-in ${a.collision_warning ? 'critical' : ''}`}>
                <div className="card-header">
                  <h2>Vehicle {a.vehicle_id}</h2>
                  <span className="timestamp">{new Date(a.timestamp * 1000).toLocaleTimeString()}</span>
                </div>
                {a.collision_warning && (
                  <div className="collision-warning">
                    ⚠️ COLLISION IMMINENT IN {a.collision_warning.time_to_impact.toFixed(1)}s (Target: V{a.collision_warning.target_id})
                  </div>
                )}
              </div>
            ))
          )}
        </main>
      </div>
    </div>
  );
}

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error("React Crash:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ color: 'white', padding: '2rem', fontFamily: 'monospace' }}>
          <h2>Frontend Crash Detected:</h2>
          <p style={{ color: '#f43f5e' }}>{this.state.error?.toString()}</p>
          <pre style={{ background: '#1e293b', padding: '1rem', whiteSpace: 'pre-wrap' }}>
            {this.state.errorInfo?.componentStack}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function AppWithErrorBoundary() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}