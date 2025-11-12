import type { Metadata } from "next";
import { Toaster } from "react-hot-toast";
import { ThemeProvider } from "@/components/providers/theme-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Projectx",
  description: "A project with a modern AI-powered agent",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider defaultTheme="dark" storageKey="projectx-theme">
          {children}
          <Toaster
            position="top-right"
            toastOptions={{
              style: {
                fontSize: '15px',
                padding: '6px 10px',
                minHeight: '32px',
              },
            }}
          />
        </ThemeProvider>
      </body>
    </html>
  );
}
