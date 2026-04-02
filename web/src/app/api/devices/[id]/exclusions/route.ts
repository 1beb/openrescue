import { getDb } from '@/lib/db'
import { NextResponse } from 'next/server'

export async function GET(request: Request, { params }: { params: { id: string } }) {
  const db = getDb()
  const exclusions = db.prepare('SELECT * FROM device_exclusions WHERE device_id = ?').all(params.id)
  return NextResponse.json(exclusions)
}

export async function POST(request: Request, { params }: { params: { id: string } }) {
  const body = await request.json()
  const { keyword } = body

  if (!keyword) {
    return NextResponse.json({ error: 'keyword required' }, { status: 400 })
  }

  const db = getDb()
  try {
    const result = db.prepare('INSERT INTO device_exclusions (device_id, keyword) VALUES (?, ?)').run(params.id, keyword)
    return NextResponse.json({ id: result.lastInsertRowid, device_id: params.id, keyword }, { status: 201 })
  } catch (e: any) {
    if (e.code === 'SQLITE_CONSTRAINT_UNIQUE') {
      return NextResponse.json({ error: 'exclusion already exists' }, { status: 409 })
    }
    throw e
  }
}
