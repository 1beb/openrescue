import { getDb } from '@/lib/db'
import { NextResponse } from 'next/server'

export async function PUT(request: Request, { params }: { params: { key: string } }) {
  const body = await request.json()
  const { value } = body

  if (value === undefined) {
    return NextResponse.json({ error: 'value required' }, { status: 400 })
  }

  const db = getDb()
  db.prepare(`
    INSERT INTO settings (device_id, key, value) VALUES (NULL, ?, ?)
    ON CONFLICT(device_id, key) DO UPDATE SET value = ?
  `).run(params.key, String(value), String(value))

  return NextResponse.json({ ok: true })
}
