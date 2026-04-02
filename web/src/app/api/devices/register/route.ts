import { getDb } from '@/lib/db'
import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  const body = await request.json()
  const { id, hostname } = body

  if (!id || !hostname) {
    return NextResponse.json({ error: 'id and hostname required' }, { status: 400 })
  }

  const db = getDb()
  db.prepare(`
    INSERT INTO devices (id, hostname, last_seen)
    VALUES (?, ?, datetime('now'))
    ON CONFLICT(id) DO UPDATE SET hostname = ?, last_seen = datetime('now')
  `).run(id, hostname, hostname)

  return NextResponse.json({ ok: true })
}
