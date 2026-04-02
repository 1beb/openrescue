import { headers } from 'next/headers'

export interface TailscaleUser {
  login: string
  name: string
}

export function getTailscaleUser(): TailscaleUser | null {
  if (process.env.TAILSCALE_AUTH_ENABLED !== 'true') {
    return { login: 'dev@localhost', name: 'Developer' }
  }

  const headerList = headers()
  const login = headerList.get('Tailscale-User-Login')
  const name = headerList.get('Tailscale-User-Name')

  if (!login) return null
  return { login, name: name || login }
}
