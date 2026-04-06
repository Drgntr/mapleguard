/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const apiBase = process.env.API_BASE_URL || 'http://localhost:8000';
    return [
      {
        source: "/api/:path*",
        destination: `${apiBase}/api/:path*`,
      },
    ];
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "msu.io" },
      { protocol: "https", hostname: "*.msu.io" },
    ],
  },
};

module.exports = nextConfig;
