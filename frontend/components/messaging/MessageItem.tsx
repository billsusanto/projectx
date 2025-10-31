"use client";

import { Message } from '@/types/messaging';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { motion } from 'framer-motion';
import { Bot, User } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MessageItemProps {
  message: Message;
}

export default function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === 'user';
  const timestamp = new Date(message.created_at).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={cn('flex gap-3', isUser ? 'justify-end' : 'justify-start')}
    >
      {!isUser && (
        <Avatar className="h-9 w-9 border-2 border-primary/20 shadow-lg">
          <AvatarFallback className="bg-gradient-to-br from-purple-600 via-blue-600 to-cyan-600">
            <Bot className="h-5 w-5 text-white" />
          </AvatarFallback>
        </Avatar>
      )}

      <div className={cn('flex max-w-[75%] flex-col', isUser ? 'items-end' : 'items-start')}>
        <motion.div
          whileHover={{ scale: 1.02 }}
          transition={{ duration: 0.2 }}
          className={cn(
            'rounded-2xl px-4 py-3 shadow-lg backdrop-blur-sm transition-all',
            isUser
              ? 'bg-gradient-to-br from-blue-600 via-blue-700 to-blue-800 text-white shadow-blue-500/25'
              : 'border border-border bg-card text-card-foreground shadow-md dark:border-border/50 dark:bg-card/50'
          )}
        >
          <p className="whitespace-pre-wrap break-words text-[15px] leading-relaxed">
            {message.content}
          </p>
        </motion.div>
        <span className="mt-1.5 px-1 text-xs text-muted-foreground">
          {timestamp}
        </span>
      </div>

      {isUser && (
        <Avatar className="h-9 w-9 border-2 border-primary/20 shadow-lg">
          <AvatarFallback className="bg-gradient-to-br from-blue-600 via-purple-600 to-pink-600">
            <User className="h-5 w-5 text-white" />
          </AvatarFallback>
        </Avatar>
      )}
    </motion.div>
  );
}
