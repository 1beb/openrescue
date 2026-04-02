'use client'

import { Button } from '@/components/button'
import { Divider } from '@/components/divider'
import { Heading, Subheading } from '@/components/heading'
import { Input } from '@/components/input'
import { Text } from '@/components/text'
import { useEffect, useState } from 'react'

interface Setting {
  key: string
  value: string
}

const SETTING_LABELS: Record<string, { label: string; description: string; type: string }> = {
  retention_days: {
    label: 'Buffer Retention',
    description: 'Number of days to keep shipped session records in the local SQLite buffer before pruning.',
    type: 'number',
  },
  poll_interval_seconds: {
    label: 'Poll Interval',
    description: 'How often (in seconds) the agent checks the active window.',
    type: 'number',
  },
  idle_threshold_seconds: {
    label: 'Idle Threshold',
    description: 'Seconds of inactivity before the agent considers you idle and stops tracking.',
    type: 'number',
  },
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    fetch('/api/settings')
      .then((r) => r.json())
      .then((data: Setting[]) => {
        const map: Record<string, string> = {}
        data.forEach((s) => (map[s.key] = s.value))
        setSettings(map)
      })
  }, [])

  async function handleSave() {
    for (const [key, value] of Object.entries(settings)) {
      await fetch(`/api/settings/${key}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value }),
      })
    }
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="mx-auto max-w-4xl">
      <Heading>Settings</Heading>
      <Divider className="my-10 mt-6" />

      {Object.entries(SETTING_LABELS).map(([key, meta]) => (
        <div key={key}>
          <section className="grid gap-x-8 gap-y-6 sm:grid-cols-2">
            <div className="space-y-1">
              <Subheading>{meta.label}</Subheading>
              <Text>{meta.description}</Text>
            </div>
            <div>
              <Input
                type={meta.type}
                value={settings[key] || ''}
                onChange={(e) => setSettings((s) => ({ ...s, [key]: e.target.value }))}
              />
            </div>
          </section>
          <Divider className="my-10" soft />
        </div>
      ))}

      <div className="flex items-center justify-end gap-4">
        {saved && <Text className="text-green-600">Saved</Text>}
        <Button onClick={handleSave}>Save changes</Button>
      </div>
    </div>
  )
}
