const path = require("path");
const { loadEnvConfig } = require("@next/env");

loadEnvConfig(path.join(__dirname, "../.."));

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  outputFileTracingRoot: path.join(__dirname, "../.."),
};

module.exports = nextConfig;
