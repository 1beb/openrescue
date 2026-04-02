import { Heading } from '@/components/heading'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Dashboard',
}

export default function Dashboard() {
  return (
    <>
      <Heading>Dashboard</Heading>
      <div className="mt-6">
        <iframe
          src="/grafana/d/openrescue-activity-overview?orgId=1&kiosk"
          className="h-[calc(100vh-12rem)] w-full rounded-lg border border-zinc-200 dark:border-zinc-700"
          title="Activity Overview"
        />
      </div>
    </>
  )
}
