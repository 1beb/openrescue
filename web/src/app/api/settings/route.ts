import { getDb } from '@/lib/db'
import { NextResponse } from 'next/server'
export const dynamic = 'force-dynamic'
export async function GET() {
  const db = getDb()
  const settings = db.prepare('SELECT * FROM settings WHERE device_id IS NULL').all()
  return NextResponse.json(settings)
}
