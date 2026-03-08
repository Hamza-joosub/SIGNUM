import type { Metadata } from "next";
import { DM_Sans, Fraunces } from "next/font/google";
import "./globals.css";

const dmSans = DM_Sans({ subsets: ["latin"], variable: "--font-dm-sans" });
const fraunces = Fraunces({
    subsets: ["latin"],
    variable: "--font-fraunces",
    style: ["normal", "italic"],
});

export const metadata: Metadata = {
    title: "QuantLab",
    description: "Cross-asset capital flow models",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body className={`${dmSans.variable} ${fraunces.variable}`}>
                {children}
            </body>
        </html>
    );
}
