'use client'

import { Button } from '@/components/button'
import { Divider } from '@/components/divider'
import { Heading, Subheading } from '@/components/heading'
import { Input } from '@/components/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/table'
import { Text } from '@/components/text'
import { useCallback, useEffect, useState } from 'react'

interface Device {
  id: string
  hostname: string
  display_name: string | null
}

interface Exclusion {
  id: number
  keyword: string
}

export default function DeviceDetailPage({ params }: { params: { id: string } }) {
  const [device, setDevice] = useState<Device | null>(null)
  const [exclusions, setExclusions] = useState<Exclusion[]>([])
  const [displayName, setDisplayName] = useState('')
  const [newExclusion, setNewExclusion] = useState('')

  const fetchDevice = useCallback(async () => {
    const res = await fetch(`/api/devices/${params.id}`)
    const d = await res.json()
    setDevice(d)
    setDisplayName(d.display_name || '')
  }, [params.id])

  const fetchExclusions = useCallback(async () => {
    const res = await fetch(`/api/devices/${params.id}/exclusions`)
    setExclusions(await res.json())
  }, [params.id])

  useEffect(() => { fetchDevice(); fetchExclusions() }, [fetchDevice, fetchExclusions])

  async function saveName() {
    await fetch(`/api/devices/${params.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ display_name: displayName }),
    })
    fetchDevice()
  }

  async function addExclusion() {
    await fetch(`/api/devices/${params.id}/exclusions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keyword: newExclusion }),
    })
    setNewExclusion('')
    fetchExclusions()
  }

  async function removeExclusion(eid: number) {
    await fetch(`/api/devices/${params.id}/exclusions/${eid}`, { method: 'DELETE' })
    fetchExclusions()
  }

  if (!device) return null

  return (
    <>
      <Heading>{device.display_name || device.hostname}</Heading>
      <Text className="mt-2">Device ID: {device.id}</Text>

      <Divider className="my-10 mt-6" />

      <section className="grid gap-x-8 gap-y-6 sm:grid-cols-2">
        <div className="space-y-1">
          <Subheading>Display Name</Subheading>
          <Text>A friendly name for this device.</Text>
        </div>
        <div className="flex gap-4">
          <Input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder={device.hostname}
          />
          <Button onClick={saveName}>Save</Button>
        </div>
      </section>

      <Divider className="my-10" soft />

      <section>
        <div className="flex items-end justify-between gap-4">
          <Subheading>Exclusions</Subheading>
        </div>
        <Text className="mt-1">Apps or keywords to exclude from tracking on this device.</Text>

        <div className="mt-4 flex gap-4">
          <Input
            placeholder="Keyword to exclude"
            value={newExclusion}
            onChange={(e) => setNewExclusion(e.target.value)}
          />
          <Button onClick={addExclusion}>Add</Button>
        </div>

        <Table className="mt-4">
          <TableHead>
            <TableRow>
              <TableHeader>Keyword</TableHeader>
              <TableHeader className="text-right">Actions</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {exclusions.map((ex) => (
              <TableRow key={ex.id}>
                <TableCell>{ex.keyword}</TableCell>
                <TableCell className="text-right">
                  <Button plain onClick={() => removeExclusion(ex.id)}>Remove</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </section>
    </>
  )
}
