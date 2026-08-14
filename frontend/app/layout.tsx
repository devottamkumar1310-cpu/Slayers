import './globals.css';
import Navbar from '@/components/Navbar';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'SLAYERS — Visual Research & Asset Sourcing Engine for Creators',
  description: 'Automates visual research, scene detection, visual intent extraction, and asset acquisition for video editors and content creators.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-gray-100 min-h-screen flex flex-col antialiased">
        <Navbar />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="border-t border-surfaceBorder py-6 text-center text-xs text-gray-500">
          <p>SLAYERS &mdash; Social Media Automation Hackathon Project</p>
        </footer>
      </body>
    </html>
  );
}
