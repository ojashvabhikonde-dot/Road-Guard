import pytest
import numpy as np
from fastapi.testclient import TestClient
from unittest import mock

# Import the FastAPI app from the AI service
from src.main import app, detect_frame, start_rtsp

client = TestClient(app)

def test_detect_frame_returns_structure():
    # Create a dummy black image (640x480)
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    detections = detect_frame(img)
    # Should return a list (may be empty if model does not detect on black image)
    assert isinstance(detections, list)
    for det in detections:
        assert "class" in det
        assert "confidence" in det
        assert "bbox" in det
        assert isinstance(det["bbox"], list) and len(det["bbox"]) == 4

def test_start_rtsp_returns_stream_id(monkeypatch):
    # Patch cv2.VideoCapture to simulate a successful capture without real video
    class DummyCap:
        def __init__(self, url):
            self.url = url
            self.counter = 0
        def isOpened(self):
            return True
        def read(self):
            if self.counter < 2:
                self.counter += 1
                # Return dummy black frame
                return True, np.zeros((480, 640, 3), dtype=np.uint8)
            return False, None
        def release(self):
            pass
    monkeypatch.setattr('cv2.VideoCapture', DummyCap)
    response = client.post("/api/v1/rtsp/start", json={"stream_url": "dummy"})
    assert response.status_code == 200
    data = response.json()
    assert "stream_id" in data
    assert data["status"] == "started"

