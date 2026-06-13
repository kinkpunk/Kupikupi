/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: "https://p01--kupikupi-api--4fc5jsdxgp9r.code.run/:path*",
      },
    ];
  },
};

export default nextConfig;
