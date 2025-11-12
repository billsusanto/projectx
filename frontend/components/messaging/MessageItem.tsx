"use client";

import { Message, MessagePart } from '@/types/messaging';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { motion } from 'framer-motion';
import { Bot, User } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ThinkingBlock } from './parts/ThinkingBlock';
import { ToolCallBlock } from './parts/ToolCallBlock';
import { TextBlock } from './parts/TextBlock';

interface MessageItemProps {
  message: Message;
}

export default function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === 'user';
  const timestamp = new Date(message.created_at).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  // Correlate tool calls with their results
  const toolCalls = new Map<string, MessagePart>();
  const toolResults = new Map<string, MessagePart>();

  for (const part of message.parts) {
    if (part.part_kind === 'tool-call' && part.tool_call_id) {
      toolCalls.set(part.tool_call_id, part);
    } else if (part.part_kind === 'tool-return' && part.tool_call_id) {
      toolResults.set(part.tool_call_id, part);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={cn('flex gap-3', isUser ? 'justify-end' : 'justify-start')}
    >
      {!isUser && (
        <Avatar className="h-9 w-9 flex-shrink-0 border-2 border-primary/20 shadow-lg">
          <AvatarFallback className="bg-gradient-to-br from-purple-600 via-blue-600 to-cyan-600">
            <Bot className="h-5 w-5 text-white" />
          </AvatarFallback>
        </Avatar>
      )}

      <div className={cn('flex max-w-[75%] flex-col gap-2', isUser ? 'items-end' : 'items-start')}>
        {message.parts.map((part, idx) => {
          // Skip system prompts (usually hidden)
          if (part.part_kind === 'system-prompt') {
            return null;
          }

          // Render thinking blocks
          if (part.part_kind === 'thinking') {
            return <ThinkingBlock key={`${message.id}-thinking-${idx}`} part={part} />;
          }

          // Render tool calls with their results
          if (part.part_kind === 'tool-call' && part.tool_call_id) {
            const result = toolResults.get(part.tool_call_id);
            return (
              <ToolCallBlock
                key={`${message.id}-tool-${part.tool_call_id}`}
                part={part}
                result={result}
              />
            );
          }

          // Skip tool returns (rendered with tool calls)
          if (part.part_kind === 'tool-return') {
            return null;
          }

          // Render text parts (both user-prompt and text)
          if (part.part_kind === 'text' || part.part_kind === 'user-prompt') {
            return (
              <TextBlock
                key={`${message.id}-text-${idx}`}
                part={part}
                isUser={isUser}
              />
            );
          }

          return null;
        })}

        <span className="mt-0.5 px-1 text-xs text-muted-foreground">
          {timestamp}
        </span>
      </div>

      {isUser && (
        <Avatar className="h-9 w-9 flex-shrink-0 border-2 border-primary/20 shadow-lg">
          <AvatarFallback className="bg-gradient-to-br from-blue-600 via-purple-600 to-pink-600">
            <User className="h-5 w-5 text-white" />
          </AvatarFallback>
        </Avatar>
      )}
    </motion.div>
  );
}
