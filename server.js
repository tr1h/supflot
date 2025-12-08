// server.js
const express = require('express');
const cors    = require('cors');
const pg      = require('pg');

const app = express();
app.use(cors());
app.use(express.json());

// Параметры вашей локальной Postgres
const pool = new pg.Pool({
  host:     'localhost',
  port:     5432,
  database: 'supbot',    // имя вашей БД
  user:     'botuser',   // ваш пользователь
  password: 'botpass'    // ваш пароль
});

// GET /locations — вернуть все локации
app.get('/locations', async (req, res) => {
  try {
    const { rows } = await pool.query('SELECT id, name FROM locations ORDER BY name');
    res.json(rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Ошибка чтения локаций' });
  }
});

// POST /bookings — вставить новую бронь
app.post('/bookings', async (req, res) => {
  const { location, datetime, name, phone } = req.body;
  if (!location || !datetime || !name || !phone) {
    return res.status(400).json({ error: 'Неполные данные' });
  }
  try {
    await pool.query(
      'INSERT INTO bookings(location, datetime, name, phone) VALUES($1, $2, $3, $4)',
      [location, datetime, name, phone]
    );
    res.json({ success: true });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Ошибка создания брони' });
  }
});

const PORT = 3000;
app.listen(PORT, () => console.log(`API-сервер слушает http://localhost:${PORT}`));
