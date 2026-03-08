/** @type {import('next').NextConfig} */
const nextConfig = {
    // In development: proxy /api/* to the local FastAPI server on port 8000.
    // In production (Vercel): /api/* is handled natively — no rewrite needed.
    rewrites: async () => {
        if (process.env.NODE_ENV !== "development") return [];
        return [
            {
                source: "/api/:path*",
                destination: "http://127.0.0.1:8000/api/:path*",
            },
        ];
    },
};

export default nextConfig;
