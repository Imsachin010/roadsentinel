const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const cors = require("cors");
const fetch = (...args) => import('node-fetch').then(({default: fetch}) => fetch(...args));

const app = express();
app.use(cors());

const server = http.createServer(app);

const io = new Server(server, {
  cors: {
    origin: "*",
  },
});

console.log("🚀 Alert server started...");

io.on("connection", (socket) => {
  console.log("Client connected:", socket.id);

  socket.on("disconnect", () => {
    console.log("Client disconnected:", socket.id);
  });
});

// Broadcast function
function broadcastAlert(alert) {
  io.emit("wrong_way_alert", alert);
}

// Expose endpoint for Python to call
app.use(express.json());

app.post("/alert", (req, res) => {
  const alert = req.body;
  console.log("🚨 Broadcasting Alert:", alert.vehicle_id);

  broadcastAlert(alert);
  res.send({ status: "sent" });
});

app.post("/telemetry", (req, res) => {
  const telemetry = req.body;
  io.emit("telemetry_update", telemetry);
  res.send({ status: "sent" });
});

// Proxy scenario switch to Python engine (avoids browser CORS on port 5001)
app.post("/scenario", async (req, res) => {
  const { scenario } = req.body;
  console.log(`🎬 Scenario switch requested: ${scenario}`);
  try {
    const response = await fetch("http://localhost:5001/scenario", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario })
    });
    const data = await response.json();
    // Broadcast scenario change to all dashboard clients
    io.emit("scenario_changed", { scenario });
    res.json(data);
  } catch (e) {
    console.error("Failed to relay scenario to engine:", e.message);
    res.status(500).json({ error: "Could not reach detection engine" });
  }
});

server.listen(5000, () => {
  console.log("Server running on port 5000");
});