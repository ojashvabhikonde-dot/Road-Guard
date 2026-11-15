import express from 'express';
import db from '../db.js';

const router = express.Router();

// GET /api/v1/detections?camera_id=...&start=ISO&end=ISO
router.get('/', async (req, res) => {
  const { camera_id, start, end } = req.query;
  let query = 'SELECT detection_id, camera_id, frame_timestamp, class, confidence, ST_AsGeoJSON(bbox) AS bbox FROM detections';
  const params = [];
  const conditions = [];
  if (camera_id) {
    params.push(camera_id);
    conditions.push(`camera_id = $${params.length}`);
  }
  if (start) {
    params.push(start);
    conditions.push(`frame_timestamp >= $${params.length}`);
  }
  if (end) {
    params.push(end);
    conditions.push(`frame_timestamp <= $${params.length}`);
  }
  if (conditions.length) {
    query += ' WHERE ' + conditions.join(' AND ');
  }
  query += ' ORDER BY frame_timestamp DESC LIMIT 100';
  try {
    const result = await db.query(query, params);
    res.json({code: 0, message: 'ok', data: result.rows});
  } catch (err) {
    console.error(err);
    res.status(500).json({code: 1, message: 'DB error'});
  }
});

export default router;

