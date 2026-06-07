import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import NavBar from "@/components/NavBar";
import EnvGuard from "@/components/EnvGuard";

export const metadata = {
  title: "VayuTask AI | India Gig Marketplace",
  description:
    "VayuTask AI — India's AI-native gig marketplace. Voice-to-task, translated chat, vision verification, and Razorpay escrow. Powered by Gemini and FastAPI.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </head>
      <body>
        <AuthProvider>
          <EnvGuard />
          <NavBar />
          <main className="main-wrapper">{children}</main>
          <footer className="footer-bar">
            <p>© 2026 VayuTask AI India. Built with Gemini &amp; FastAPI.</p>
          </footer>
        </AuthProvider>

        <style dangerouslySetInnerHTML={{ __html: `
          .main-wrapper {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 24px 80px 24px;
            min-height: calc(100vh - 180px);
          }
          .footer-bar {
            text-align: center;
            padding: 30px 24px;
            color: var(--color-text-muted);
            font-size: 0.85rem;
            border-top: 1px solid var(--border-glow);
          }
        ` }} />
      </body>
    </html>
  );
}
