-- Risk events table
CREATE TABLE IF NOT EXISTS risk_events (
    risk_id UUID PRIMARY KEY,
    vehicle_id UUID NOT NULL,
    camera_id UUID REFERENCES cameras(camera_id),
    relative_speed_kmh DOUBLE PRECISION NOT NULL,
    distance_to_queue_m DOUBLE PRECISION NOT NULL,
    ttc_seconds DOUBLE PRECISION,
    estimated_stopping_distance_m DOUBLE PRECISION,
    risk_score INT NOT NULL,
    risk_level TEXT NOT NULL,          -- LOW, MODERATE, HIGH, CRITICAL
    confidence DOUBLE PRECISION,
    metadata JSONB,
    timestamp TIMESTAMPTZ NOT NULL,
    location GEOGRAPHY(POINT, 4326),   -- optional vehicle position
    created_at TIMESTAMPTZ DEFAULT now()
);

