const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const cors = require("cors");

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

server.listen(5000, () => {
  console.log("Server running on port 5000");
});