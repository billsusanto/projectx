import { useRef, useState, useEffect, useCallback } from 'react';
import { ConnectionStatus, SendMessagePayload } from '@/types/messaging';

interface UseWebSocketOptions {
  onMessage?: (event: MessageEvent) => void;
}

interface UseWebSocketReturn {
  connectionStatus: ConnectionStatus;
  sendMessage: (data: SendMessagePayload) => void;
  error: Error | null;
}

export function useWebSocket(options?: UseWebSocketOptions): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const onMessageRef = useRef(options?.onMessage);

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(
    ConnectionStatus.DISCONNECTED
  );
  const [error, setError] = useState<Error | null>(null);

  // Keep onMessage callback ref updated
  useEffect(() => {
    onMessageRef.current = options?.onMessage;
  }, [options?.onMessage]);

  useEffect(() => {
    const connect = () => {
      try {
        const wsUrl = 'ws://localhost:8000/messaging/ws';
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        setConnectionStatus(ConnectionStatus.CONNECTING);
        setError(null);

        ws.onopen = () => {
          console.log('WebSocket connected');
          setConnectionStatus(ConnectionStatus.CONNECTED);
          reconnectAttemptsRef.current = 0;
          setError(null);
        };

        ws.onmessage = (event) => {
          if (onMessageRef.current) {
            onMessageRef.current(event);
          }
        };

        ws.onerror = (event) => {
          console.error('WebSocket error:', event);
          setError(new Error('WebSocket connection error'));
          setConnectionStatus(ConnectionStatus.ERROR);
        };

        ws.onclose = () => {
          console.log('WebSocket closed');
          setConnectionStatus(ConnectionStatus.DISCONNECTED);
          wsRef.current = null;

          // Auto-reconnect with exponential backoff
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1})`);

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connect();
          }, delay);
        };
      } catch (err) {
        console.error('Failed to create WebSocket:', err);
        setError(err instanceof Error ? err : new Error('Unknown error'));
        setConnectionStatus(ConnectionStatus.ERROR);
      }
    };

    connect();

    return () => {
      console.log('Cleaning up WebSocket');
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const sendMessage = useCallback((data: SendMessagePayload) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected');
      setError(new Error('Cannot send message: WebSocket is not connected'));
      return;
    }

    try {
      wsRef.current.send(JSON.stringify(data));
    } catch (err) {
      console.error('Failed to send message:', err);
      setError(err instanceof Error ? err : new Error('Failed to send message'));
    }
  }, []);

  return {
    connectionStatus,
    sendMessage,
    error,
  };
}
