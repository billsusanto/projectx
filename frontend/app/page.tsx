"use client";

import MessagingInterface from '@/components/messaging/MessagingInterface';
import { ThemeToggle } from '@/components/theme-toggle';
import { motion } from 'framer-motion';

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col bg-gradient-to-br from-background via-background to-muted/20">
      {/* Floating Theme Toggle */}
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3, delay: 0.2 }}
        className="fixed left-6 top-6 z-50"
      >
        <ThemeToggle />
      </motion.div>

      {/* Main Content */}
      <div className="h-screen overflow-hidden p-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mx-auto h-full max-w-6xl"
        >
          <MessagingInterface />
        </motion.div>
      </div>

      {/* Decorative Background Elements */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -left-1/4 top-0 h-96 w-96 rounded-full bg-blue-500/10 blur-3xl" />
        <div className="absolute -right-1/4 bottom-0 h-96 w-96 rounded-full bg-purple-500/10 blur-3xl" />
      </div>
    </main>
  );
}