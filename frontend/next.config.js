/** @type {import('next').NextConfig} */
module.exports = {
  reactStrictMode: true,
  // "standalone" is for self-hosting/Docker only. Vercel builds its own output,
  // so it is skipped there (Vercel sets the VERCEL env var during builds).
  ...(process.env.VERCEL ? {} : { output: "standalone" }),
};
