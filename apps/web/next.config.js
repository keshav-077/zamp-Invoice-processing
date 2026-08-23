const path = require("path");
const fs = require("fs");
const { loadEnvConfig } = require("@next/env");

const repoRoot = path.join(__dirname, "../..");
const isMonorepoRoot =
  fs.existsSync(path.join(repoRoot, "package.json")) &&
  fs.existsSync(path.join(repoRoot, "apps", "web", "package.json"));

loadEnvConfig(isMonorepoRoot ? repoRoot : __dirname);

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  outputFileTracingRoot: isMonorepoRoot ? repoRoot : __dirname,
  async rewrites() {
    const apiUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
