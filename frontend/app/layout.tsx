import type { Metadata } from "next";
import "./globals.css";
import { ClerkProvider, Show, SignInButton, SignUpButton } from "@clerk/nextjs";
import { AuthProvider } from "@/lib/auth-context";
import Header from "@/components/Header";

export const metadata: Metadata = {
  title: "MatchMind",
  description: "AI-powered personality matchmaking",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col bg-gray-950 text-gray-100 antialiased">
        <ClerkProvider>
          <AuthProvider>
            <header className="border-b border-gray-900 bg-gray-950/80 px-4 py-2 text-right backdrop-blur">
              <Show when="signed-out">
                <div className="inline-flex gap-2">
                  <SignInButton forceRedirectUrl="/chat" mode="modal" />
                  <SignUpButton forceRedirectUrl="/profile" mode="modal" />
                </div>
              </Show>
            </header>
            <Header />
            <main className="flex flex-1 flex-col">{children}</main>
          </AuthProvider>
        </ClerkProvider>
      </body>
    </html>
  );
}
