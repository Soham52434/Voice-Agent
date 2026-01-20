/** @type {import('next').NextConfig} */
const nextConfig = {
  // Optimized for production deployment (Railway)
  output: 'standalone',
  // Railway handles port automatically via PORT env var
  // Next.js will use PORT if provided, otherwise defaults to 3000
};

module.exports = nextConfig;
