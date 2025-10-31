"use client";

import { ConnectionStatus as ConnectionStatusEnum } from '@/types/chat';
import { Badge } from '@/components/ui/badge';
import { motion, AnimatePresence } from 'framer-motion';
import { Wifi, WifiOff, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ConnectionStatusProps {
  status: ConnectionStatusEnum;
}

export default function ConnectionStatus({ status }: ConnectionStatusProps) {
  if (status === ConnectionStatusEnum.CONNECTED) {
    return null;
  }

  const getStatusConfig = () => {
    switch (status) {
      case ConnectionStatusEnum.CONNECTING:
        return {
          variant: 'default' as const,
          className: 'border-yellow-500/50 bg-yellow-500/10 text-yellow-700 dark:text-yellow-400',
          icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
          message: 'Connecting to server...',
        };
      case ConnectionStatusEnum.DISCONNECTED:
        return {
          variant: 'destructive' as const,
          className: 'border-orange-500/50 bg-orange-500/10 text-orange-700 dark:text-orange-400',
          icon: <WifiOff className="h-3.5 w-3.5" />,
          message: 'Disconnected. Reconnecting...',
        };
      case ConnectionStatusEnum.ERROR:
        return {
          variant: 'destructive' as const,
          className: 'border-red-500/50 bg-red-500/10 text-red-700 dark:text-red-400',
          icon: <AlertCircle className="h-3.5 w-3.5" />,
          message: 'Connection error. Please check your network.',
        };
      default:
        return null;
    }
  };

  const config = getStatusConfig();
  if (!config) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.3 }}
        className="border-b border-border/50 bg-muted/30 px-6 py-3 backdrop-blur-sm"
        role="alert"
        aria-live="polite"
      >
        <div className="mx-auto flex max-w-4xl items-center justify-center gap-2">
          <Badge
            variant={config.variant}
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 text-xs font-medium shadow-lg',
              config.className
            )}
          >
            {config.icon}
            <span>{config.message}</span>
          </Badge>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
