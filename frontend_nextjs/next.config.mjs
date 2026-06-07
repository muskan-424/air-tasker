/** @type {import('next').NextConfig} */
const apiRewriteTarget =
  process.env.NEXT_PUBLIC_API_REWRITE_TARGET || "http://localhost:4000";

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiRewriteTarget.replace(/\/$/, "")}/api/:path*`,
      },
    ];
  },
  // Allow img tags from external sources used in verification demo
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'images.unsplash.com' },
    ],
  },
};

export default nextConfig;
