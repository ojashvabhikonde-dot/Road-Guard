import express from 'express';
import db from '../db.js';

const router = express.Router();

// List cameras
router.get('/', async (req, res) => {
  try {
    const result = await db.query('SELECT * FROM cameras');
    res.json({code: 0, message: 'ok', data: result.rows});
  } catch (err) {
    console.error(err);
    res.status(500).json({code: 1, message: 'DB error'});
  }
});

// Get camera status
router.get('/:id/status', async (req, res) => {
  const {id} = req.params;
  try {
    const result = await db.query('SELECT status FROM cameras WHERE camera_id = $1', [id]);
    if (result.rowCount === 0) return res.status(404).json({code: 1, message: 'Camera not found'});
    res.json({code: 0, message: 'ok', data: {camera_id: id, status: result.rows[0].status}});
  } catch (err) {
    console.error(err);
    res.status(500).json({code: 1, message: 'DB error'});
  }
});

export default router;

