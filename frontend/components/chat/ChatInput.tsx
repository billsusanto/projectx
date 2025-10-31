'use client';

import { useState, useRef, useEffect, FormEvent, KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { motion } from 'framer-motion';
import { Send, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled: boolean;
  isLoading: boolean;
}

export default function ChatInput({ onSend, disabled, isLoading }: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();

    const trimmedMessage = message.trim();
    if (!trimmedMessage || disabled || isLoading) return;

    onSend(trimmedMessage);
    setMessage('');

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  useEffect(() => {
    if (!textareaRef.current) return;

    textareaRef.current.style.height = 'auto';
    const scrollHeight = textareaRef.current.scrollHeight;
    textareaRef.current.style.height = Math.min(scrollHeight, 150) + 'px';
  }, [message]);

  return (
    <div className="border-t border-border/50 bg-background/80 p-6 backdrop-blur-xl">
      <form onSubmit={handleSubmit} className="mx-auto max-w-4xl">
        <motion.div
          animate={{
            scale: isFocused ? 1.01 : 1,
          }}
          transition={{ duration: 0.2 }}
          className={cn(
            'relative flex gap-3 rounded-2xl border-2 bg-card p-3 shadow-xl transition-all',
            isFocused
              ? 'border-primary/50 shadow-2xl shadow-primary/10'
              : 'border-border/50 shadow-lg'
          )}
        >
          <div className="relative flex-1">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder="Type your message..."
              disabled={disabled}
              rows={1}
              className="w-full resize-none bg-transparent px-2 py-2 pr-12 text-[15px] leading-relaxed text-foreground placeholder:text-muted-foreground focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
              aria-label="Message input"
              style={{ minHeight: '40px', maxHeight: '150px' }}
            />
            {message.length > 0 && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                className="absolute bottom-2 right-2 rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground"
              >
                {message.length}/5000
              </motion.div>
            )}
          </div>

          <Button
            type="submit"
            size="icon"
            disabled={disabled || isLoading || !message.trim()}
            className="h-12 w-12 flex-shrink-0 rounded-xl bg-gradient-to-br from-blue-600 via-blue-700 to-purple-700 text-white shadow-lg shadow-blue-500/25 transition-all hover:scale-105 hover:shadow-xl hover:shadow-blue-500/30 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
            aria-label="Send message"
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </Button>
        </motion.div>

        <div className="mt-3 flex items-center justify-center gap-1 text-xs text-muted-foreground">
          <kbd className="rounded bg-muted px-2 py-1 font-mono text-[11px] font-medium">Enter</kbd>
          <span>to send</span>
          <span className="mx-1">•</span>
          <kbd className="rounded bg-muted px-2 py-1 font-mono text-[11px] font-medium">Shift + Enter</kbd>
          <span>for new line</span>
        </div>
      </form>
    </div>
  );
}
