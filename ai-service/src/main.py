import os
import cv2
import numpy as np
import asyncio
import json
from uuid import uuid4
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from typing import List, Dict, Set

from .db import get_db

app = FastAPI(title="ROADGUARD AI Service")

# CORS (frontend on localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load pretrained YOLO model (YOLOv8n for speed)
MODEL_PATH = os.getenv("YOLO_MODEL", "yolov8n.pt")
model = YOLO(MODEL_PATH)

# In‑memory structures for active streams and websocket clients
active_streams: Dict[str, asyncio.Task] = {}
active_ws: Set[WebSocket] = set()

# Helper to run detection on a frame
def detect_frame(frame: np.ndarray) -> List[Dict]:
    results = model(frame, verbose=False)[0]
    detections = []
    for box in results.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        xyxy = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
        detections.append({
            "class_id": cls_id,
            "class": model.names[cls_id],
            "confidence": conf,
            "bbox": xyxy,
        })
    return detections

# Broadcast payload to all connected websocket clients
def broadcast_detection(payload: dict):
    message = json.dumps(payload)
    dead: Set[WebSocket] = set()
    for ws in active_ws:
        try:
            asyncio.create_task(ws.send_text(message))
        except Exception:
            dead.add(ws)
    for ws in dead:
        active_ws.discard(ws)

# DB connection lifecycle
@app.on_event("startup")
async def startup_event():
    db = await get_db()
    await db.connect()

@app.on_event("shutdown")
async def shutdown_event():
    db = await get_db()
    await db.close()

# Video upload endpoint (placeholder)
@app.post("/api/v1/video/upload")
async def upload_video(file: UploadFile = File(...)):
    """Accept an MP4 video for batch processing (demo placeholder)."""
    if not file.filename.lower().endswith('.mp4'):
        raise HTTPException(status_code=400, detail="Only MP4 files are supported.")
    video_id = str(uuid4())
    temp_path = f"/tmp/{video_id}.mp4"
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)
    return JSONResponse({"video_id": video_id, "status": "queued"})

# WebSocket for detections – clients receive real detections broadcast by streams
@app.websocket("/ws/detections")
async def detections_ws(ws: WebSocket):
    await ws.accept()
    active_ws.add(ws)
    try:
        while True:
            await ws.receive_text()  # keep connection alive; client can send pings
    except WebSocketDisconnect:
        active_ws.discard(ws)

# Start RTSP stream and process frames
@app.post("/api/v1/rtsp/start")
async def start_rtsp(stream_url: str):
    """Start processing an RTSP stream and push detections via WebSocket."""
    stream_id = str(uuid4())

    async def stream_task():
        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            return
        db = await get_db()
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            detections = detect_frame(frame)
            observations = []
            for det in detections:
                x1, y1, x2, y2 = det["bbox"]
                detection_id = str(uuid4())
                polygon_wkt = f"POLYGON(({x1} {y1}, {x2} {y1}, {x2} {y2}, {x1} {y2}, {x1} {y1}))"
                await db.execute(
                    "INSERT INTO detections (detection_id, camera_id, frame_timestamp, class, confidence, bbox) "
                    "VALUES ($1, $2, $3, $4, $5, ST_GeomFromText($6, 4326))",
                    detection_id, "cam-demo", datetime.utcnow(), det["class"], det["confidence"], polygon_wkt,
                )
                # For demo purposes, assign placeholder speed/distance values
                obs = Observation(
                    detection_id=detection_id,
                    speed_mps=10.0,
                    distance_m=30.0,
                    road_type="city",
                )
                observations.append(obs)
            # Evaluate risk for collected observations
            if observations:
                results = evaluate_batch(observations)
                for res in results:
                    await db.execute(
                        "INSERT INTO risk_events (event_id, detection_id, risk_score, risk_level, description) VALUES ($1, $2, $3, $4, $5)",
                        str(uuid4()), res.detection_id, res.risk_score, res.risk_level, res.description,
                    )
            payload = {
                "stream_id": stream_id,
                "timestamp": datetime.utcnow().isoformat(),
                "detections": detections,
            }
            broadcast_detection(payload)
            await asyncio.sleep(0.03)
        cap.release()

    task = asyncio.create_task(stream_task())
    active_streams[stream_id] = task
    return {"stream_id": stream_id, "status": "started"}

# Stop RTSP stream
@app.post("/api/v1/rtsp/stop")
async def stop_rtsp(stream_id: str):
    task = active_streams.get(stream_id)
    if task:
        task.cancel()
        del active_streams[stream_id]
        return {"stream_id": stream_id, "status": "stopped"}
    raise HTTPException(status_code=404, detail="Stream ID not found")

# Risk evaluation endpoint
from typing import List
from .risk import evaluate_batch, Observation
import uuid

@app.post("/api/v1/risk/evaluate")
async def risk_evaluate(observations: List[Observation]):
    results = evaluate_batch(observations)
    db = await get_db()
    for res in results:
        await db.execute(
            "INSERT INTO risk_events (event_id, detection_id, risk_score, risk_level, description) VALUES ($1, $2, $3, $4, $5)",
            str(uuid.uuid4()), res.detection_id, res.risk_score, res.risk_level, res.description
        )
    return {"code": 0, "message": "ok", "data": [r.dict() for r in results]}


# Risk evaluation endpoint
from typing import List
from .risk import evaluate_batch, Observation
import uuid

@app.post("/api/v1/risk/evaluate")
async def risk_evaluate(observations: List[Observation]):
    results = evaluate_batch(observations)
    db = await get_db()
    for res in results:
        await db.execute(
            "INSERT INTO risk_events (event_id, detection_id, risk_score, risk_level, description) VALUES ($1, $2, $3, $4, $5)",
            str(uuid.uuid4()), res.detection_id, res.risk_score, res.risk_level, res.description
        )
    return {"code": 0, "message": "ok", "data": [r.dict() for r in results]}

