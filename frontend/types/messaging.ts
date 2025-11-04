import type { components } from './types';

export type MessageRead = components['schemas']['MessageRead'];
export type ConversationRead = components['schemas']['ConversationRead'];
export type MessageRole = components['schemas']['MessageRoleEnum'];

export enum ConnectionStatus {
    CONNECTING = 'connecting',
    CONNECTED = 'connected',
    DISCONNECTED = 'disconnected',
    ERROR = 'error',
}

export interface MessagePart {
    part_kind: 'text' | 'thinking' | 'tool-call' | 'tool-return' | 'user-prompt' | 'system-prompt';
    content?: string;

    // Thinking-specific fields
    provider_name?: string;
    signature?: string;
    id?: string;

    // Tool-specific fields
    tool_name?: string;
    tool_call_id?: string;
    args?: Record<string, any>;
    metadata?: Record<string, any>;
    timestamp?: string;
}

export type WebSocketMessage =
    | { type: 'conversation_created'; conversation_id: number }
    | {
        type: 'message';
        id: number;
        parts: MessagePart[];
        role: MessageRole;
        conversation_id: number;
        created_at: string;
        model_name?: string;
        timestamp?: string;
      }
    | {
        type: 'message_part';
        message_id: number;
        part: MessagePart;
        role: MessageRole;
        conversation_id: number;
      }
    | {
        type: 'node_added';
        message_id: number;
        node: {
          id: string;
          step: number;
          parts: MessagePart[];
          model_name?: string;
          timestamp?: string;
        };
        conversation_id: number;
      }
    | {
        type: 'text_chunk';
        message_id: number;
        chunk: string;
        role: MessageRole;
        conversation_id: number;
      }
    | {
        type: 'message_complete';
        id: number;
        role: MessageRole;
        conversation_id: number;
        created_at: string;
        model_name?: string;
        timestamp?: string;
      }
    | {
        type: 'tool_start';
        message_id: number;
        tool_name: string;
        args: Record<string, any>;
        conversation_id: number;
      }
    | {
        type: 'tool_complete';
        message_id: number;
        tool_name: string;
        result: any;
        conversation_id: number;
      }
    | { type: 'error'; error: string };

export interface SendMessagePayload {
    content: string;
    conversation_id?: number;
}

export interface Message {
    id: number | string;
    parts: MessagePart[];
    role: MessageRole;
    created_at: string;
    model_name?: string;
    timestamp?: string;
    isOptimistic?: boolean;
}
