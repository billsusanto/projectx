import { useState, useCallback } from 'react';
import { flushSync } from 'react-dom';
import { useWebSocket } from './useWebsocket';
import { Message, WebSocketMessage, ConnectionStatus, MessagePart } from '@/types/messaging';

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
            parts: data.parts,
            role: data.role,
            created_at: data.created_at,
            model_name: data.model_name ?? undefined,
            timestamp: data.timestamp ?? undefined,
          };

          // Add message to array if it doesn't already exist
          setMessages((prev) => {
            const exists = prev.find((m) => m.id === newMessage.id);
            if (exists) return prev;
            return [...prev, newMessage];
          });

          // If agent message, stop loading
          if (data.role === 'AGENT') {
            setIsLoading(false);
          }
          break;

        case 'message_part':
          console.log('Received message part:', data);
          setMessages((prev) => {
            const existingIndex = prev.findIndex((m) => m.id === data.message_id);

            if (existingIndex >= 0) {
              // Message exists, append the part
              const updated = [...prev];
              updated[existingIndex] = {
                ...updated[existingIndex],
                parts: [...updated[existingIndex].parts, data.part],
              };
              return updated;
            } else {
              // Create new message with this part
              const newMsg: Message = {
                id: data.message_id,
                parts: [data.part],
                role: data.role,
                created_at: new Date().toISOString(), // Temporary, will be updated on complete
              };
              return [...prev, newMsg];
            }
          });
          break;

        case 'node_added':
          console.log('Received node:', data.node);
          setMessages((prev) => {
            const existingIndex = prev.findIndex((m) => m.id === data.message_id);

            if (existingIndex >= 0) {
              // Message exists, append all parts from this node (with deduplication)
              const updated = [...prev];
              const existingParts = updated[existingIndex].parts;

              // Deduplicate tool parts by tool_call_id
              const newParts = data.node.parts.filter((newPart) => {
                if ((newPart.part_kind === 'tool-call' || newPart.part_kind === 'tool-return') && newPart.tool_call_id) {
                  // Check if this tool_call_id already exists
                  return !existingParts.some(
                    (existingPart) =>
                      existingPart.part_kind === newPart.part_kind &&
                      existingPart.tool_call_id === newPart.tool_call_id
                  );
                }
                return true; // Include non-tool parts
              });

              updated[existingIndex] = {
                ...updated[existingIndex],
                parts: [...existingParts, ...newParts],
                model_name: data.node.model_name || updated[existingIndex].model_name,
                timestamp: data.node.timestamp || updated[existingIndex].timestamp,
              };
              return updated;
            } else {
              // Create new message with these parts
              const newMsg: Message = {
                id: data.message_id,
                parts: data.node.parts,
                role: 'AGENT',
                created_at: new Date().toISOString(),
                model_name: data.node.model_name ?? undefined,
                timestamp: data.node.timestamp ?? undefined,
              };
              return [...prev, newMsg];
            }
          });
          break;

        case 'text_chunk':
          console.log('Received text chunk:', data.chunk);
          setMessages((prev) => {
            const existingIndex = prev.findIndex((m) => m.id === data.message_id);

            if (existingIndex >= 0) {
              // Message exists, update or create text part
              const updated = [...prev];
              const message = updated[existingIndex];

              // Find the last text part to append to
              const lastPartIndex = message.parts.findLastIndex((p) => p.part_kind === 'text');

              if (lastPartIndex >= 0) {
                // Append to existing text part
                const updatedParts = [...message.parts];
                updatedParts[lastPartIndex] = {
                  ...updatedParts[lastPartIndex],
                  content: (updatedParts[lastPartIndex].content || '') + data.chunk,
                };
                updated[existingIndex] = {
                  ...message,
                  parts: updatedParts,
                };
              } else {
                // Create new text part
                updated[existingIndex] = {
                  ...message,
                  parts: [
                    ...message.parts,
                    {
                      part_kind: 'text',
                      content: data.chunk,
                    },
                  ],
                };
              }
              return updated;
            } else {
              // Create new message with text chunk
              const newMsg: Message = {
                id: data.message_id,
                parts: [
                  {
                    part_kind: 'text',
                    content: data.chunk,
                  },
                ],
                role: data.role,
                created_at: new Date().toISOString(),
              };
              return [...prev, newMsg];
            }
          });
          break;

        case 'message_complete':
          console.log('Message complete:', data);
          setMessages((prev) => {
            const existingIndex = prev.findIndex((m) => m.id === data.id);
            if (existingIndex >= 0) {
              // Update the message with final metadata
              const updated = [...prev];
              updated[existingIndex] = {
                ...updated[existingIndex],
                created_at: data.created_at,
                model_name: data.model_name ?? undefined,
                timestamp: data.timestamp ?? undefined,
              };
              return updated;
            }
            return prev;
          });
          setIsLoading(false);
          break;

        case 'tool_start':
          console.log('Tool started:', data);
          // Use flushSync to force immediate render before tool_complete arrives
          flushSync(() => {
            setMessages((prev) => {
              const existingIndex = prev.findIndex((m) => m.id === data.message_id);

              const toolCallPart: MessagePart = {
                part_kind: 'tool-call',
                tool_name: data.tool_name,
                tool_call_id: `${data.tool_name}-${Date.now()}`,
                args: data.args,
              };

              if (existingIndex >= 0) {
                const updated = [...prev];
                updated[existingIndex] = {
                  ...updated[existingIndex],
                  parts: [...updated[existingIndex].parts, toolCallPart],
                };
                return updated;
              } else {
                // Create new message if it doesn't exist
                const newMsg: Message = {
                  id: data.message_id,
                  parts: [toolCallPart],
                  role: 'AGENT',
                  created_at: new Date().toISOString(),
                };
                return [...prev, newMsg];
              }
            });
          });
          break;

        case 'tool_complete':
          console.log('Tool completed:', data);
          setMessages((prev) => {
            const existingIndex = prev.findIndex((m) => m.id === data.message_id);

            if (existingIndex >= 0) {
              const updated = [...prev];
              const message = updated[existingIndex];

              // Find the matching tool call to get its ID
              const toolCall = message.parts.find(
                (p) => p.part_kind === 'tool-call' && p.tool_name === data.tool_name
              );

              const toolReturnPart: MessagePart = {
                part_kind: 'tool-return',
                tool_name: data.tool_name,
                tool_call_id: toolCall?.tool_call_id || `${data.tool_name}-return`,
                content: typeof data.result === 'string' ? data.result : JSON.stringify(data.result),
                status: data.status || 'success',
                error_message: data.error_message,
              };

              updated[existingIndex] = {
                ...message,
                parts: [...message.parts, toolReturnPart],
              };
              return updated;
            }
            return prev;
          });
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
