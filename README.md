# ROADGUARD AI

## Running Module 1 (Traffic Detection & Monitoring) locally

### Prerequisites
- **Docker Desktop** (or Docker Engine) installed.
- **Node 20** (for the backend and frontend).
- **Python 3.11** (for the AI service).
- **npm** (comes with Node) and **pip**.

### 1️⃣ Start the infrastructure
```bash
cd "D:\projects\traffic app"
# Build and start PostgreSQL+PostGIS, Redis, backend, AI service, and frontend containers
docker compose up -d
```
This will:
- Launch a PostGIS database listening on `localhost:5432`.
- Start Redis on `localhost:6379`.
- Run the Express backend on `localhost:4000`.
- Run the FastAPI AI service on `localhost:8000`.
- Serve the React UI on `localhost:3000`.

### 2️⃣ Install dependencies for each service (one‑time only)
```bash
# Backend
cd backend && npm install && cd ..
# Frontend
cd frontend && npm install && cd ..
# AI Service (virtualenv recommended)
cd ai-service && python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt && cd ..
```

### 3️⃣ Run the services (if you prefer manual mode)
```bash
# Backend
cd backend && npm start & cd ..
# AI Service (development)
cd ai-service && .venv\Scripts\activate && uvicorn src.main:app --reload & cd ..
# Frontend (development)
cd frontend && npm run dev
```

### 4️⃣ Open the dashboard
Open your browser at `http://localhost:3000/module1`. You should see:
- A video player (replace `frontend/public/sample-video.mp4` with any short MP4 of highway footage).
- Real‑time bounding‑box overlay drawn on the canvas.
- KPI cards showing total cameras, detections per frame, and active streams.

### 5️⃣ Test the end‑to‑end flow
1. **Start an RTSP (or file) stream** – for demo you can feed the same MP4 file via the RTSP endpoint:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/rtsp/start" -H "Content-Type: application/json" -d '{"stream_url": "file:///tmp/<your‑video‑id>.mp4"}'
   ```
2. **Verify detections are stored**:
   ```bash
   curl http://localhost:4000/api/v1/detections
   ```
   You should receive a JSON list of detection rows.
3. **Watch the UI** – the canvas overlay should update as detections arrive.

### 6️⃣ Run the automated test suite
```bash
# From the repository root
cd ai-service && .venv\Scripts\activate && pytest
```
The suite includes:
- **Unit tests** for the YOLO detection helper.
- **Database tests** that mock `asyncpg` to ensure the INSERT statement is built correctly.
- **Integration test** that starts the FastAPI app with `TestClient`, simulates a short video stream, and checks that detections are persisted and returned via the API.

### 7️⃣ Stop the stack
```bash
docker compose down
```

---
*When all tests pass and the UI shows live detections, Module 1 meets its completion criteria (see `module1_plan.md`).*
