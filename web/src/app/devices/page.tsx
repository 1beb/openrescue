'use client'

import { Heading } from '@/components/heading'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/table'
import { useEffect, useState } from 'react'

interface Device {
  id: string
  hostname: string
  display_name: string | null
  last_seen: string | null
}

export default function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([])

  useEffect(() => {
    fetch('/api/devices').then(r => r.json()).then(setDevices)
  }, [])

  return (
    <>
      <Heading>Devices</Heading>
      <Table className="mt-8 [--gutter:--spacing(6)] lg:[--gutter:--spacing(10)]">
        <TableHead>
          <TableRow>
            <TableHeader>Name</TableHeader>
            <TableHeader>Hostname</TableHeader>
            <TableHeader>Last Seen</TableHeader>
          </TableRow>
        </TableHead>
        <TableBody>
          {devices.map((device) => (
            <TableRow key={device.id} href={`/devices/${device.id}`}>
              <TableCell className="font-medium">
                {device.display_name || device.hostname}
              </TableCell>
              <TableCell className="text-zinc-500">{device.hostname}</TableCell>
              <TableCell className="text-zinc-500">
                {device.last_seen ? new Date(device.last_seen + 'Z').toLocaleString() : 'Never'}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </>
  )
}
