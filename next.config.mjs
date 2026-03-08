/** @type {import('next').NextConfig} */
const nextConfig = {
    // In development: proxy /api/* to local FastAPI server on port 8000.
    // In production (Vercel): no rewrite needed — vercel.json routes /api/*
    // directly to the Python serverless function.
    ...(process.env.NODE_ENV === "development" && {
        rewrites: async () => [
            {
                source: "/api/:path*",
                destination: "http://127.0.0.1:8000/api/:path*",
            },
        ],
    }),
};

export default nextConfig;
