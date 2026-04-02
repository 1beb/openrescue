import { getDb } from '@/lib/db'

import { NextResponse } from 'next/server'
export const dynamic = 'force-dynamic'

const VALID_CATEGORIES = ['very_productive', 'productive', 'distracting', 'very_distracting']

export async function PUT(request: Request, { params }: { params: { id: string } }) {
  const body = await request.json()
  const { keyword, category } = body

  if (category && !VALID_CATEGORIES.includes(category)) {
    return NextResponse.json({ error: `category must be one of: ${VALID_CATEGORIES.join(', ')}` }, { status: 400 })
  }

  const db = getDb()
  if (keyword && category) {
    db.prepare('UPDATE category_rules SET keyword = ?, category = ? WHERE id = ?').run(keyword, category, params.id)
  } else if (category) {
    db.prepare('UPDATE category_rules SET category = ? WHERE id = ?').run(category, params.id)
  } else if (keyword) {
    db.prepare('UPDATE category_rules SET keyword = ? WHERE id = ?').run(keyword, params.id)
  }

  return NextResponse.json({ ok: true })
}

export async function DELETE(request: Request, { params }: { params: { id: string } }) {
  const db = getDb()
  db.prepare('DELETE FROM category_rules WHERE id = ?').run(params.id)
  return NextResponse.json({ ok: true })
}
