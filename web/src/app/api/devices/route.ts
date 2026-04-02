import { getDb } from '@/lib/db'
import { NextResponse } from 'next/server'

export async function GET() {
  const db = getDb()
  const devices = db.prepare('SELECT * FROM devices ORDER BY last_seen DESC').all()
  return NextResponse.json(devices)
}
