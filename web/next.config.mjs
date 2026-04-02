/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/grafana/:path*',
        destination: `${process.env.GRAFANA_URL || 'http://localhost:3000'}/:path*`,
      },
    ]
  },
}

export default nextConfig
