import { getDb } from '@/lib/db'
import { NextResponse } from 'next/server'

export async function PUT(request: Request, { params }: { params: { id: string } }) {
  const body = await request.json()
  const { display_name } = body

  const db = getDb()
  db.prepare('UPDATE devices SET display_name = ? WHERE id = ?').run(display_name, params.id)

  return NextResponse.json({ ok: true })
}

export async function GET(request: Request, { params }: { params: { id: string } }) {
  const db = getDb()
  const device = db.prepare('SELECT * FROM devices WHERE id = ?').get(params.id)
  if (!device) {
    return NextResponse.json({ error: 'not found' }, { status: 404 })
  }
  return NextResponse.json(device)
}
