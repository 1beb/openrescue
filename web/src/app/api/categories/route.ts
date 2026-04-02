import { getDb } from '@/lib/db'
import { NextResponse } from 'next/server'

const VALID_CATEGORIES = ['very_productive', 'productive', 'distracting', 'very_distracting']

export async function GET() {
  const db = getDb()
  const rules = db.prepare('SELECT * FROM category_rules ORDER BY category, keyword').all()
  return NextResponse.json(rules)
}

export async function POST(request: Request) {
  const body = await request.json()
  const { keyword, category } = body

  if (!keyword || !category) {
    return NextResponse.json({ error: 'keyword and category required' }, { status: 400 })
  }
  if (!VALID_CATEGORIES.includes(category)) {
    return NextResponse.json({ error: `category must be one of: ${VALID_CATEGORIES.join(', ')}` }, { status: 400 })
  }

  const db = getDb()
  try {
    const result = db.prepare('INSERT INTO category_rules (keyword, category) VALUES (?, ?)').run(keyword, category)
    return NextResponse.json({ id: result.lastInsertRowid, keyword, category }, { status: 201 })
  } catch (e: any) {
    if (e.code === 'SQLITE_CONSTRAINT_UNIQUE') {
      return NextResponse.json({ error: 'keyword already exists' }, { status: 409 })
    }
    throw e
  }
}
