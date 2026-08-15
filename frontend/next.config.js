/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Asset thumbnails come from an open-ended set of provider CDNs (Wikimedia,
  // Pexels, Unsplash, brand hosts, and whatever a new provider adds), so the
  // asset cards use plain <img> rather than next/image. No remote allow-list is
  // needed, and a new provider can never be silently blocked at render time.
  poweredByHeader: false,
};

module.exports = nextConfig;
