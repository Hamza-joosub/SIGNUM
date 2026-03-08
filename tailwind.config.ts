import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                background: "var(--background)",
                foreground: "var(--foreground)",
                canvas: "#080d18",
                gold: {
                    500: "#c8a96e",
                    600: "#a8883e"
                },
                olive: {
                    500: "#8ab870",
                    600: "#6a9858"
                },
                negative: {
                    500: "#c86060",
                    600: "#d87070"
                }
            },
            backgroundImage: {
                "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
            },
            fontFamily: {
                fraunces: ['var(--font-fraunces)'],
                dmsans: ['var(--font-dm-sans)'],
            }
        },
    },
    plugins: [],
};
export default config;
