import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Evaluation Pipeline",
  description: "Run and monitor AWS Bedrock evaluation jobs",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <div className="min-h-screen bg-gray-50">
            <header className="border-b border-gray-200 bg-white">
              <div className="container mx-auto px-4 py-4">
                <h1 className="text-xl font-semibold text-gray-900">
                  Evaluation Pipeline
                </h1>
                <p className="text-sm text-gray-500">
                  Run LLM-as-a-judge evaluations on AgentCore agents
                </p>
              </div>
            </header>
            <main className="container mx-auto px-4 py-8">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
