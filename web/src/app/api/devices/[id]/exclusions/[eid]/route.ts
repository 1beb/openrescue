import { getDb } from '@/lib/db'
import { NextResponse } from 'next/server'

export async function DELETE(request: Request, { params }: { params: { id: string; eid: string } }) {
  const db = getDb()
  db.prepare('DELETE FROM device_exclusions WHERE id = ? AND device_id = ?').run(params.eid, params.id)
  return NextResponse.json({ ok: true })
}
