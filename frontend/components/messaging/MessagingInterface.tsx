'use client';

import { useMessaging } from '@/hooks/useMessaging';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import { ConnectionStatus as ConnectionStatusEnum } from '@/types/messaging';
import { Card } from '@/components/ui/card';
import { motion } from 'framer-motion';
import { useEffect, useRef } from 'react';
import toast from 'react-hot-toast';
import { WifiOff, Wifi } from 'lucide-react';

export default function MessagingInterface() {
  const { messages, sendMessage, isLoading, connectionStatus } = useMessaging();
  const previousStatusRef = useRef<ConnectionStatusEnum>(connectionStatus);

  const isDisconnected =
    connectionStatus === ConnectionStatusEnum.DISCONNECTED ||
    connectionStatus === ConnectionStatusEnum.ERROR;

  const getStatusColor = () => {
    switch (connectionStatus) {
      case ConnectionStatusEnum.CONNECTED:
        return 'bg-green-500';
      case ConnectionStatusEnum.CONNECTING:
        return 'bg-orange-500';
      case ConnectionStatusEnum.DISCONNECTED:
      case ConnectionStatusEnum.ERROR:
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusShadow = () => {
    switch (connectionStatus) {
      case ConnectionStatusEnum.CONNECTED:
        return 'shadow-green-500/50';
      case ConnectionStatusEnum.CONNECTING:
        return 'shadow-orange-500/50';
      case ConnectionStatusEnum.DISCONNECTED:
      case ConnectionStatusEnum.ERROR:
        return 'shadow-red-500/50';
      default:
        return 'shadow-gray-500/50';
    }
  };

  // Show toast notifications for connection status changes
  useEffect(() => {
    const previousStatus = previousStatusRef.current;

    if (previousStatus === connectionStatus) return;

    if (connectionStatus === ConnectionStatusEnum.DISCONNECTED) {
      toast.error(
        (t) => (
          <div className="flex items-center gap-2">
            <WifiOff className="h-4 w-4" />
            <span>Reconnecting...</span>
          </div>
        ),
        {
          id: 'connection-status',
          duration: Infinity,
        }
      );
    } else if (connectionStatus === ConnectionStatusEnum.CONNECTING && previousStatus === ConnectionStatusEnum.DISCONNECTED) {
      toast.loading(
        (t) => (
          <div className="flex items-center gap-2">
            <span>Reconnecting...</span>
          </div>
        ),
        {
          id: 'connection-status',
          duration: Infinity,
        }
      );
    } else if (connectionStatus === ConnectionStatusEnum.CONNECTED && previousStatus !== ConnectionStatusEnum.CONNECTING) {
      toast.success(
        (t) => (
          <div className="flex items-center gap-2">
            <Wifi className="h-4 w-4" />
            <span>Connected</span>
          </div>
        ),
        {
          id: 'connection-status',
          duration: 2000,
        }
      );
    } else if (connectionStatus === ConnectionStatusEnum.CONNECTED) {
      toast.dismiss('connection-status');
    } else if (connectionStatus === ConnectionStatusEnum.ERROR) {
      toast.error(
        (t) => (
          <div className="flex items-center gap-2">
            <WifiOff className="h-4 w-4" />
            <span>Connection error</span>
          </div>
        ),
        {
          id: 'connection-status',
          duration: Infinity,
        }
      );
    }

    previousStatusRef.current = connectionStatus;
  }, [connectionStatus]);

  return (
    <Card className="relative flex h-full flex-col overflow-hidden border-2 border-border/50 bg-card/50 shadow-2xl backdrop-blur-sm">
      {/* Connection Status Indicator - Only show when there are messages */}
      {messages.length > 0 && (
        <div className="absolute left-4 top-4 z-10">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={
              connectionStatus === ConnectionStatusEnum.CONNECTING
                ? { scale: [1, 1.3, 1], opacity: [0.8, 1, 0.8] }
                : { opacity: 1, scale: 1 }
            }
            transition={{
              duration: 1.5,
              repeat: connectionStatus === ConnectionStatusEnum.CONNECTING ? Infinity : 0,
              ease: 'easeInOut',
            }}
            className={`h-3 w-3 rounded-full ${getStatusColor()} shadow-lg ${getStatusShadow()}`}
            title={
              connectionStatus === ConnectionStatusEnum.CONNECTED
                ? 'Connected'
                : connectionStatus === ConnectionStatusEnum.CONNECTING
                ? 'Connecting...'
                : 'Disconnected'
            }
          />
        </div>
      )}

      <MessageList messages={messages} />

      <MessageInput onSend={sendMessage} disabled={isDisconnected} isLoading={isLoading} />
    </Card>
  );
}
