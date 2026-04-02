import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  if (request.nextUrl.pathname.startsWith('/api/config/') ||
      request.nextUrl.pathname.startsWith('/api/devices/register')) {
    return NextResponse.next()
  }

  if (process.env.TAILSCALE_AUTH_ENABLED !== 'true') {
    return NextResponse.next()
  }

  const tailscaleUser = request.headers.get('Tailscale-User-Login')
  if (!tailscaleUser) {
    return new NextResponse('Unauthorized', { status: 401 })
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
