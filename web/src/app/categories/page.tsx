'use client'

import { Button } from '@/components/button'
import { Dialog, DialogActions, DialogBody, DialogTitle } from '@/components/dialog'
import { Heading } from '@/components/heading'
import { Input } from '@/components/input'
import { Select } from '@/components/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/table'
import { useCallback, useEffect, useState } from 'react'

interface CategoryRule {
  id: number
  keyword: string
  category: string
}

const CATEGORY_LABELS: Record<string, string> = {
  very_productive: 'Very Productive',
  productive: 'Productive',
  distracting: 'Distracting',
  very_distracting: 'Very Distracting',
}

export default function CategoriesPage() {
  const [rules, setRules] = useState<CategoryRule[]>([])
  const [isAddOpen, setIsAddOpen] = useState(false)
  const [newKeyword, setNewKeyword] = useState('')
  const [newCategory, setNewCategory] = useState('very_productive')

  const fetchRules = useCallback(async () => {
    const res = await fetch('/api/categories')
    setRules(await res.json())
  }, [])

  useEffect(() => { fetchRules() }, [fetchRules])

  async function handleAdd() {
    await fetch('/api/categories', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keyword: newKeyword, category: newCategory }),
    })
    setNewKeyword('')
    setIsAddOpen(false)
    fetchRules()
  }

  async function handleDelete(id: number) {
    await fetch(`/api/categories/${id}`, { method: 'DELETE' })
    fetchRules()
  }

  async function handleCategoryChange(id: number, category: string) {
    await fetch(`/api/categories/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category }),
    })
    fetchRules()
  }

  return (
    <>
      <div className="flex items-end justify-between gap-4">
        <Heading>Categories</Heading>
        <Button onClick={() => setIsAddOpen(true)}>Add Rule</Button>
      </div>

      <Table className="mt-8 [--gutter:--spacing(6)] lg:[--gutter:--spacing(10)]">
        <TableHead>
          <TableRow>
            <TableHeader>Keyword</TableHeader>
            <TableHeader>Category</TableHeader>
            <TableHeader className="text-right">Actions</TableHeader>
          </TableRow>
        </TableHead>
        <TableBody>
          {rules.map((rule) => (
            <TableRow key={rule.id}>
              <TableCell className="font-medium">{rule.keyword}</TableCell>
              <TableCell>
                <Select
                  value={rule.category}
                  onChange={(e) => handleCategoryChange(rule.id, e.target.value)}
                  className="w-48"
                >
                  {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </Select>
              </TableCell>
              <TableCell className="text-right">
                <Button plain onClick={() => handleDelete(rule.id)}>Delete</Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Dialog open={isAddOpen} onClose={setIsAddOpen}>
        <DialogTitle>Add Category Rule</DialogTitle>
        <DialogBody>
          <div className="space-y-4">
            <div>
              <Input
                placeholder="Keyword (e.g. github.com, slack)"
                value={newKeyword}
                onChange={(e) => setNewKeyword(e.target.value)}
              />
            </div>
            <div>
              <Select value={newCategory} onChange={(e) => setNewCategory(e.target.value)}>
                {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </Select>
            </div>
          </div>
        </DialogBody>
        <DialogActions>
          <Button plain onClick={() => setIsAddOpen(false)}>Cancel</Button>
          <Button onClick={handleAdd}>Add</Button>
        </DialogActions>
      </Dialog>
    </>
  )
}
