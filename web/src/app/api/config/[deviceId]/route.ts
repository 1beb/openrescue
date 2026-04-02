import { getDb } from '@/lib/db'

import { NextResponse } from 'next/server'
export const dynamic = 'force-dynamic'

export async function GET(request: Request, { params }: { params: { deviceId: string } }) {
  const db = getDb()

  db.prepare("UPDATE devices SET last_seen = datetime('now') WHERE id = ?").run(params.deviceId)

  const rules = db.prepare('SELECT keyword, category FROM category_rules').all() as {
    keyword: string
    category: string
  }[]

  const categories: Record<string, string[]> = {
    very_productive: [],
    productive: [],
    distracting: [],
    very_distracting: [],
  }
  for (const rule of rules) {
    if (categories[rule.category]) {
      categories[rule.category].push(rule.keyword)
    }
  }

  const exclusions = db
    .prepare('SELECT keyword FROM device_exclusions WHERE device_id = ?')
    .all(params.deviceId) as { keyword: string }[]

  const globalSettings = db
    .prepare("SELECT key, value FROM settings WHERE device_id IS NULL")
    .all() as { key: string; value: string }[]

  const deviceSettings = db
    .prepare('SELECT key, value FROM settings WHERE device_id = ?')
    .all(params.deviceId) as { key: string; value: string }[]

  const settings: Record<string, string> = {}
  for (const s of globalSettings) settings[s.key] = s.value
  for (const s of deviceSettings) settings[s.key] = s.value

  return NextResponse.json({
    categories,
    exclusions: exclusions.map((e) => e.keyword),
    settings,
  })
}
