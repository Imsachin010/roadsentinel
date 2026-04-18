import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, Circle, Marker, Polyline, Popup } from "react-leaflet";
import L from "leaflet";
import { io } from "socket.io-client";
import { LineChart, Line, Tooltip, ResponsiveContainer } from "recharts";
import "leaflet/dist/leaflet.css";
import "./App.css";

const BROADCASTER_URL = import.meta.env.VITE_BROADCASTER_URL || "http://localhost:5000";
const socket = io(BROADCASTER_URL, {
  transports: ["polling"]  // Force polling — Railway blocks WebSocket upgrades on free tier
});

// ── Sparkline tooltip ──────────────────────────────────────────────────────────
const SparkTooltip = ({ active, payload }) => {
  if (active && payload?.length) {
    return (
      <div style={{ background: "#1e293b", padding: "4px 8px", borderRadius: 4, fontSize: 11, color: "#f8fafc" }}>
        {(payload[0].value * 100).toFixed(0)}%
      </div>
    );
  }
  return null;
};

// ── Alert Card ─────────────────────────────────────────────────────────────────
function AlertCard({ alert, history, scenario }) {
  const conf = (alert.confidence ?? 0) * 100;
  const isCritical = !!alert.collision_warning;
  const isHigh = alert.severity === "HIGH";

  return (
    <div className={`alert-card fade-in ${isCritical ? "critical" : isHigh ? "high" : ""} scenario-${scenario}`}>
      <div className="card-header">
        <h2>
          {scenario === "ghost" && "🚨 "}
          {scenario === "normal" && "✅ "}
          {scenario === "false_positive" && "🟡 "}
          Vehicle {alert.vehicle_id}
        </h2>
        <span className={`severity-badge ${isHigh ? "badge-high" : "badge-medium"}`}>
          {alert.severity ?? "MEDIUM"}
        </span>
      </div>

      <div className="card-meta">
        <div className="meta-item">
          <span className="meta-label">Confidence</span>
          <span className="meta-value conf-value">{conf.toFixed(0)}%</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Road Type</span>
          <span className="meta-value">{alert.road_type ?? "—"}</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Time</span>
          <span className="meta-value">
            {alert.timestamp ? new Date(alert.timestamp * 1000).toLocaleTimeString() : "—"}
          </span>
        </div>
      </div>

      {/* Confidence Sparkline */}
      {history && history.length > 1 && (
        <div className="sparkline-wrap">
          <span className="meta-label">Confidence History</span>
          <ResponsiveContainer width="100%" height={40}>
            <LineChart data={history.map((c, i) => ({ t: i, c }))}>
              <Tooltip content={<SparkTooltip />} />
              <Line
                type="monotone"
                dataKey="c"
                stroke={isHigh ? "#f43f5e" : "#f97316"}
                dot={false}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {isCritical && (
        <div className="collision-warning">
          ⚠️ COLLISION IN {alert.collision_warning.time_to_impact.toFixed(1)}s — Target V{alert.collision_warning.target_id}
        </div>
      )}
    </div>
  );
}

// ── Main App ───────────────────────────────────────────────────────────────────
function App() {
  const [vehicles, setVehicles] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [confHistory, setConfHistory] = useState({});
  const [posHistory, setPosHistory] = useState({});  // motion trails
  const [scenario, setScenario] = useState("normal");
  const [switching, setSwitching] = useState(false);

  const switchScenario = async (s) => {
    setSwitching(true);
    try {
      await fetch(`${BROADCASTER_URL}/scenario`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario: s })
      });
      setScenario(s);
      setAlerts([]);
      setConfHistory({});
      setPosHistory({});    // clear trails
      setVehicles({});      // clear stale markers
    } catch (e) {
      console.error("Scenario switch failed:", e);
    } finally {
      setSwitching(false);
    }
  };

  useEffect(() => {
    socket.on("telemetry_update", (frame) => {
      // Update motion trail positions
      setPosHistory((prev) => {
        const next = { ...prev };
        frame.forEach((v) => {
          const trail = prev[v.vehicle_id] || [];
          next[v.vehicle_id] = [...trail, [v.lat, v.lon]].slice(-6); // keep last 6 pts
        });
        return next;
      });

      setVehicles((prev) => {
        const next = { ...prev };
        frame.forEach((v) => {
          const existing = prev[v.vehicle_id] || {};
          // Merge position/speed from telemetry BUT preserve alert metadata
          next[v.vehicle_id] = {
            ...existing,
            lat: v.lat,
            lon: v.lon,
            heading: v.heading,
            speed: v.speed,
            vehicle_id: v.vehicle_id,
            // Keep alert-specific fields from previous state, don't overwrite
            isAlert: existing.isAlert || false,
            confidence: existing.confidence,
            severity: existing.severity,
            road_type: existing.road_type,
            collision_warning: existing.collision_warning,
          };
        });
        return next;
      });
    });

    socket.on("wrong_way_alert", (data) => {
      // Update alert list (latest up top, max 50)
      setAlerts((prev) => [data, ...prev].slice(0, 50));

      // Mark on map
      setVehicles((prev) => ({
        ...prev,
        [data.vehicle_id]: { ...prev[data.vehicle_id], ...data, isAlert: true }
      }));

      // Track confidence over time per vehicle
      setConfHistory((prev) => {
        const old = prev[data.vehicle_id] ?? [];
        return {
          ...prev,
          [data.vehicle_id]: [...old, data.confidence ?? 0].slice(-20)
        };
      });
    });

    return () => {
      socket.off("telemetry_update");
      socket.off("wrong_way_alert");
    };
  }, []);

  const createIcon = (heading, isAlert) => {
    const rotation = (heading || 0) - 90;
    return L.divIcon({
      html: `<div class="vehicle-arrow ${isAlert ? "alerted" : "normal"}" style="transform:rotate(${rotation}deg)">➤</div>`,
      className: "custom-div-icon",
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });
  };

  return (
    <div className="cockpit">
      {/* ── LEFT: Map ──────────────────── */}
      <div className="map-pane">
        <MapContainer center={[13.0827, 80.2707]} zoom={13} style={{ height: "100%", width: "100%" }}>
          <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" />

          {Object.values(vehicles).map((v) => (
            <React.Fragment key={v.vehicle_id}>
              {/* Motion Trail */}
              {posHistory[v.vehicle_id]?.length > 1 && (
                <Polyline
                  positions={posHistory[v.vehicle_id]}
                  pathOptions={{
                    color: v.isAlert ? "#f43f5e" : "#475569",
                    weight: 2,
                    opacity: 0.5,
                    dashArray: v.isAlert ? null : "4, 6"
                  }}
                />
              )}

              <Marker position={[v.lat, v.lon]} icon={createIcon(v.heading, v.isAlert)}>
                <Popup>
                  <strong>Vehicle {v.vehicle_id}</strong><br />
                  Speed: {v.speed?.toFixed(1)} m/s<br />
                  {v.confidence && <>Confidence: {(v.confidence * 100).toFixed(0)}%<br /></>}
                  {v.severity && <>Severity: {v.severity}</>}
                </Popup>
              </Marker>

              {v.isAlert && (
                <Circle
                  center={[v.lat, v.lon]}
                  radius={200}
                  pathOptions={{ color: "#f43f5e", fillColor: "#f43f5e", fillOpacity: 0.15, weight: 1.5 }}
                />
              )}

              {v.isAlert && v.collision_warning && vehicles[v.collision_warning.target_id] && (
                <Polyline
                  positions={[
                    [v.lat, v.lon],
                    [vehicles[v.collision_warning.target_id].lat, vehicles[v.collision_warning.target_id].lon]
                  ]}
                  pathOptions={{ color: "#eab308", weight: 3, dashArray: "8, 8" }}
                />
              )}
            </React.Fragment>
          ))}
        </MapContainer>
      </div>

      {/* ── RIGHT: Cockpit Panel ────────── */}
      <div className="side-pane">
        <header className="header">
          <h1>🚨 RoadSentinel</h1>
          <p className="subtitle">Connected Cockpit Hub</p>
          <div className="status-indicator">
            <span className="dot pulse" /> Telemetry Active
          </div>

          {/* Scenario Switcher */}
          <div className="scenario-bar">
            <span className="meta-label" style={{marginBottom: 6, display:'block'}}>Scenario</span>
            <div className="scenario-buttons">
              {["normal", "ghost", "false_positive"].map((s) => (
                <button
                  key={s}
                  className={`scenario-btn ${scenario === s ? "active-" + s : ""}`}
                  onClick={() => switchScenario(s)}
                  disabled={switching}
                >
                  {s === "normal" && "🟢 Normal"}
                  {s === "ghost" && "🔴 Ghost Driver"}
                  {s === "false_positive" && "🟡 FP Test"}
                </button>
              ))}
            </div>
          </div>

          <div className="stat-row">
            <div className="stat-box">
              <span className="stat-num">{Object.keys(vehicles).length}</span>
              <span className="stat-label">Vehicles</span>
            </div>
            <div className="stat-box">
              <span className="stat-num" style={{ color: "#f43f5e" }}>
                {Object.values(vehicles).filter((v) => v.isAlert).length}
              </span>
              <span className="stat-label">Threats</span>
            </div>
            <div className="stat-box">
              <span className="stat-num" style={{ color: "#eab308" }}>
                {alerts.filter((a) => a.collision_warning).length}
              </span>
              <span className="stat-label">Collisions</span>
            </div>
          </div>
        </header>

        <main className="alerts-container">
          {alerts.length === 0 ? (
            <div className="empty-state">No anomalies detected.<br />Traffic flow nominal.</div>
          ) : (
            alerts.map((a, i) => (
              <AlertCard
                key={`${a.vehicle_id}-${i}`}
                alert={a}
                history={confHistory[a.vehicle_id]}
                scenario={scenario}
              />
            ))
          )}
        </main>
      </div>
    </div>
  );
}

// ── Error Boundary ─────────────────────────────────────────────────────────────
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error("React Crash:", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ color: "white", padding: "2rem", fontFamily: "monospace" }}>
          <h2>Frontend Crash Detected:</h2>
          <p style={{ color: "#f43f5e" }}>{this.state.error?.toString()}</p>
          <pre style={{ background: "#1e293b", padding: "1rem", whiteSpace: "pre-wrap" }}>
            {this.state.errorInfo?.componentStack}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function AppWithErrorBoundary() {
  return <ErrorBoundary><App /></ErrorBoundary>;
}