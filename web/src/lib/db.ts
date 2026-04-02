import Database from 'better-sqlite3'
import path from 'path'

const DB_PATH = process.env.DATABASE_PATH || path.join(process.cwd(), 'data', 'settings.db')

let db: Database.Database | null = null

export function getDb(): Database.Database {
  if (!db) {
    const dir = path.dirname(DB_PATH)
    const fs = require('fs')
    fs.mkdirSync(dir, { recursive: true })

    db = new Database(DB_PATH)
    db.pragma('journal_mode = WAL')
    db.pragma('foreign_keys = ON')
    initSchema(db)
  }
  return db
}

function initSchema(db: Database.Database) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS devices (
      id TEXT PRIMARY KEY,
      hostname TEXT NOT NULL,
      display_name TEXT,
      last_seen TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS category_rules (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      keyword TEXT NOT NULL UNIQUE,
      category TEXT NOT NULL CHECK(category IN ('very_productive', 'productive', 'distracting', 'very_distracting')),
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS device_exclusions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
      keyword TEXT NOT NULL,
      UNIQUE(device_id, keyword)
    );

    CREATE TABLE IF NOT EXISTS settings (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      device_id TEXT REFERENCES devices(id) ON DELETE CASCADE,
      key TEXT NOT NULL,
      value TEXT NOT NULL,
      UNIQUE(device_id, key)
    );
  `)

  const existing = db.prepare("SELECT count(*) as c FROM settings WHERE device_id IS NULL").get() as { c: number }
  if (existing.c === 0) {
    const insert = db.prepare("INSERT OR IGNORE INTO settings (device_id, key, value) VALUES (NULL, ?, ?)")
    insert.run('retention_days', '10')
    insert.run('poll_interval_seconds', '5')
    insert.run('idle_threshold_seconds', '300')
  }
}
