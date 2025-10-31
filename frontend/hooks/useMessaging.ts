import { useState, useCallback } from 'react';
import { useWebSocket } from './useWebsocket';
import { Message, WebSocketMessage, ConnectionStatus } from '@/types/messaging';

interface UseMessagingReturn {
  messages: Message[];
  conversationId: number | null;
  sendMessage: (content: string) => void;
  isLoading: boolean;
  connectionStatus: ConnectionStatus;
  error: Error | null;
}

export function useMessaging(): UseMessagingReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleWebSocketMessage = useCallback((event: MessageEvent) => {
    try {
      const data: WebSocketMessage = JSON.parse(event.data);

      switch (data.type) {
        case 'conversation_created':
          console.log('Conversation created:', data.conversation_id);
          setConversationId(data.conversation_id);
          break;

        case 'message':
          console.log('Received message:', data);
          const newMessage: Message = {
            id: data.id,
            content: data.content,
            role: data.role,
            created_at: data.created_at,
          };

          // Add message to array if it doesn't already exist
          setMessages((prev) => {
            const exists = prev.find((m) => m.id === newMessage.id);
            if (exists) return prev;
            return [...prev, newMessage];
          });

          // If agent message, stop loading
          if (data.role === 'agent') {
            setIsLoading(false);
          }
          break;

        case 'error':
          console.error('WebSocket error message:', data.error);
          setIsLoading(false);
          break;

        default:
          console.warn('Unknown message type:', data);
      }
    } catch (err) {
      console.error('Failed to parse WebSocket message:', err);
    }
  }, []);

  const { connectionStatus, sendMessage: wsSendMessage, error } = useWebSocket({
    onMessage: handleWebSocketMessage,
  });

  const sendMessage = useCallback(
    (content: string) => {
      if (!content.trim()) return;

      setIsLoading(true);

      wsSendMessage({
        content: content.trim(),
        conversation_id: conversationId || undefined,
      });
    },
    [conversationId, wsSendMessage]
  );

  return {
    messages,
    conversationId,
    sendMessage,
    isLoading,
    connectionStatus,
    error,
  };
}
