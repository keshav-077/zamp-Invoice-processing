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
};

module.exports = nextConfig;
